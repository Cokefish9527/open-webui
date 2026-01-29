import hashlib
import logging
import secrets
import time
import uuid
from datetime import datetime
from contextlib import contextmanager
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from threading import Lock
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import Column, Integer, Numeric, String, Text, func, text
from sqlalchemy.orm import Session

from open_webui.config import CREDIT_DEFAULT_CREDIT
from open_webui.env import DATABASE_SCHEMA, SRC_LOG_LEVELS, ADMIN_DATABASE_SCHEMA
from open_webui.internal.db import Base, get_db
from open_webui.internal.db_admin import get_admin_db
from open_webui.internal.migrations import ensure_coupon_schema

from ._timestamp_utils import EpochTimestamp, normalize_optional_timestamp, normalize_required_timestamp
from .credits import Credit, CreditLog, Credits, CreditLogModel, SetCreditFormDetail

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

_SCHEMA_LOCK = Lock()
_SCHEMA_READY = False


def _ensure_coupon_schema(session: Session) -> None:
    global _SCHEMA_READY
    if _SCHEMA_READY:
        return
    with _SCHEMA_LOCK:
        if _SCHEMA_READY:
            return
        ensure_coupon_schema(session.get_bind(), schema=DATABASE_SCHEMA, logger=log.debug)
        _SCHEMA_READY = True


def _admin_table_name(table: str) -> str:
    schema = (ADMIN_DATABASE_SCHEMA or "").strip()
    if schema:
        return f"{schema}.{table}"
    return table


def _log_admin_company_credit_change(
    *,
    company_id: Optional[str],
    balance_before: Decimal,
    balance_after: Decimal,
    user_id: str,
) -> None:
    """
    Best-effort: write CompanyCreditLog into admin DB so backend credit logs can display coupon redeem changes.
    """
    if not company_id:
        return
    try:
        change_amount = abs(balance_after - balance_before)
        change_type = "increase" if balance_after >= balance_before else "decrease"
        stmt = text(
            f"""
INSERT INTO {_admin_table_name("company_credit_logs")}
    (id, company_id, change_type, change_amount, balance_before, balance_after, operator_id, operated_at, remark)
VALUES
    (:id, :company_id, :change_type, :change_amount, :balance_before, :balance_after, :operator_id, :operated_at, :remark)
"""
        )
        with get_admin_db() as db:
            db.execute(
                stmt,
                {
                    "id": uuid.uuid4().hex,
                    "company_id": company_id,
                    "change_type": change_type,
                    "change_amount": change_amount,
                    "balance_before": balance_before,
                    "balance_after": balance_after,
                    "operator_id": 0,
                    "operated_at": datetime.utcnow(),
                    "remark": f"coupon redeem by user {user_id}",
                },
            )
            db.commit()
    except Exception as exc:
        log.warning("Failed to write company_credit_logs for coupon redeem: %s", exc)


@contextmanager
def _schema_aware_db():
    with get_db() as db:
        _ensure_coupon_schema(db)
        yield db


class CouponStatus(str, Enum):
    UNUSED = "UNUSED"
    USED = "USED"
    DESTROYED = "DESTROYED"


class CouponBatch(Base):
    __tablename__ = "hsai_coupon_batches"

    id = Column(String, primary_key=True)
    channel = Column(String(255), nullable=False, index=True)
    face_value = Column(Numeric(precision=24, scale=12), nullable=False)
    valid_from = Column(EpochTimestamp(), nullable=True)
    expires_at = Column(EpochTimestamp(), nullable=True, index=True)
    quantity = Column(Integer, nullable=False)
    code_prefix = Column(String(64), nullable=True)
    created_by_user_id = Column(String, nullable=True)
    remark = Column(Text, nullable=True)
    created_at = Column(EpochTimestamp(), nullable=False, index=True)
    updated_at = Column(EpochTimestamp(), nullable=False)


class Coupon(Base):
    __tablename__ = "hsai_coupons"

    id = Column(String, primary_key=True)
    batch_id = Column(String, nullable=True, index=True)
    code = Column(String(64), nullable=False, unique=True, index=True)
    channel = Column(String(255), nullable=False, index=True)
    face_value = Column(Numeric(precision=24, scale=12), nullable=False)
    valid_from = Column(EpochTimestamp(), nullable=True)
    expires_at = Column(EpochTimestamp(), nullable=True, index=True)
    status = Column(String(16), nullable=False, index=True)
    used_by_user_id = Column(String, nullable=True, index=True)
    used_at = Column(EpochTimestamp(), nullable=True)
    destroyed_by_user_id = Column(String, nullable=True)
    destroyed_at = Column(EpochTimestamp(), nullable=True)
    destroy_reason = Column(Text, nullable=True)
    created_at = Column(EpochTimestamp(), nullable=False, index=True)
    updated_at = Column(EpochTimestamp(), nullable=False)


class CouponRedeemTxn(Base):
    __tablename__ = "hsai_coupon_redeem_txns"

    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False, index=True)
    total_face_value = Column(Numeric(precision=24, scale=12), nullable=False)
    total_count = Column(Integer, nullable=False)
    success_count = Column(Integer, nullable=False)
    failed_count = Column(Integer, nullable=False)
    request_fingerprint = Column(String(128), nullable=True)
    client_ip = Column(String(64), nullable=True)
    created_at = Column(EpochTimestamp(), nullable=False, index=True)


class CouponBatchCreateForm(BaseModel):
    channel: str = Field(min_length=1, max_length=255)
    face_value: Decimal = Field(gt=Decimal("0"))
    valid_from: Optional[int] = None
    expires_at: Optional[int] = None
    quantity: int = Field(ge=1, le=100000)
    code_prefix: Optional[str] = Field(default=None, max_length=32)
    remark: Optional[str] = Field(default=None, max_length=2000)

    @field_validator("valid_from", "expires_at", mode="before")
    @classmethod
    def _validate_ts(cls, value):
        return normalize_optional_timestamp(value)


class CouponBatchCreateResponse(BaseModel):
    batch_id: str
    quantity: int
    created_at: int


class CouponRedeemForm(BaseModel):
    coupons: str = Field(description="券码列表，使用\\n换行分隔")


class CouponRedeemItem(BaseModel):
    code: str = Field(description="券码")
    status: str = Field(description="处理结果状态：REDEEMED|FAILED")
    face_value: Optional[Decimal] = Field(default=None, description="本券面额（仅成功时返回）")
    reason: Optional[str] = Field(
        default=None,
        description=(
            "失败原因（仅失败时返回）：NOT_FOUND|DESTROYED|USED|NOT_YET_VALID|EXPIRED|DUPLICATED_IN_REQUEST"
        ),
    )


class CouponRedeemResponse(BaseModel):
    success: bool = Field(description="接口是否处理成功（即使部分券码失败也可能为 true）")
    user_id: str = Field(description="当前登录用户ID")
    total_submitted: int = Field(description="提交的券码条数（去除空行后，含请求内重复）")
    total_deduped: int = Field(description="去重后的券码条数（实际参与校验/兑换）")
    total_redeemed: int = Field(description="成功兑换的券码数量")
    total_failed: int = Field(description="失败的券码数量（含请求内重复导致的失败项）")
    total_added_credit: Decimal = Field(description="本次累计入账积分")
    credit_balance_after: Decimal = Field(description="入账后的积分余额")
    items: List[CouponRedeemItem] = Field(description="逐券码处理明细（可能包含重复券码的失败项）")


class CouponUpdateForm(BaseModel):
    channel: Optional[str] = Field(default=None, max_length=255)
    face_value: Optional[Decimal] = Field(default=None, gt=Decimal("0"))
    valid_from: Optional[int] = None
    expires_at: Optional[int] = None
    remark: Optional[str] = Field(default=None, max_length=2000)

    @field_validator("valid_from", "expires_at", mode="before")
    @classmethod
    def _validate_ts(cls, value):
        return normalize_optional_timestamp(value)


class CouponDestroyForm(BaseModel):
    reason: str = Field(min_length=1, max_length=2000)


class CouponData(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    batch_id: Optional[str] = None
    code: str
    channel: str
    face_value: Decimal
    valid_from: Optional[int] = None
    expires_at: Optional[int] = None
    status: str
    used_by_user_id: Optional[str] = None
    used_at: Optional[int] = None
    destroyed_by_user_id: Optional[str] = None
    destroyed_at: Optional[int] = None
    destroy_reason: Optional[str] = None
    created_at: int
    updated_at: int


def _parse_coupon_codes(raw: str) -> Tuple[List[str], Dict[str, int], int]:
    """
    Parse coupon codes from a user-submitted string.

    Returns:
      - deduped codes (keep first occurrence order)
      - duplicates map: code -> duplicate_count (excluding first)
      - submitted count (including empty lines filtered out)
    """
    if raw is None:
        return [], {}, 0
    codes = [line.strip() for line in raw.replace("\r\n", "\n").split("\n")]
    codes = [c for c in codes if c]
    submitted = len(codes)
    deduped: List[str] = []
    seen: Dict[str, int] = {}
    dups: Dict[str, int] = {}
    for c in codes:
        if c in seen:
            dups[c] = dups.get(c, 0) + 1
            continue
        seen[c] = 1
        deduped.append(c)
    return deduped, dups, submitted


def _fingerprint(user_id: str, codes: Sequence[str]) -> str:
    payload = (user_id + "\n" + "\n".join(codes)).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _now() -> int:
    return int(time.time())


def _gen_code(*, prefix: str = "", length: int = 16) -> str:
    """
    Generate uppercase coupon code avoiding ambiguous chars.
    """
    alphabet = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"  # no 0/O/1/I
    suffix_len = max(4, length - len(prefix))
    return f"{prefix}{''.join(secrets.choice(alphabet) for _ in range(suffix_len))}"


@dataclass(frozen=True)
class RedeemDecision:
    status: str
    reason: Optional[str] = None


class CouponsTable:
    def create_batch(
        self,
        *,
        form: CouponBatchCreateForm,
        created_by_user_id: Optional[str],
    ) -> CouponBatchCreateResponse:
        batch_id = uuid.uuid4().hex
        now = _now()

        prefix = (form.code_prefix or "").strip().upper()
        if prefix and not prefix.isalnum():
            raise HTTPException(status_code=400, detail="code_prefix must be alphanumeric")

        with _schema_aware_db() as db:
            batch = CouponBatch(
                id=batch_id,
                channel=form.channel,
                face_value=form.face_value,
                valid_from=form.valid_from,
                expires_at=form.expires_at,
                quantity=form.quantity,
                code_prefix=prefix or None,
                created_by_user_id=created_by_user_id,
                remark=form.remark,
                created_at=now,
                updated_at=now,
            )
            db.add(batch)

            existing_codes: set[str] = set()
            created: List[Coupon] = []
            # Best-effort uniqueness without excessive DB roundtrips.
            for _ in range(form.quantity):
                for _attempt in range(20):
                    code = _gen_code(prefix=prefix, length=16)
                    if code in existing_codes:
                        continue
                    existing_codes.add(code)
                    created.append(
                        Coupon(
                            id=uuid.uuid4().hex,
                            batch_id=batch_id,
                            code=code,
                            channel=form.channel,
                            face_value=form.face_value,
                            valid_from=form.valid_from,
                            expires_at=form.expires_at,
                            status=CouponStatus.UNUSED.value,
                            created_at=now,
                            updated_at=now,
                        )
                    )
                    break
                else:
                    raise HTTPException(status_code=500, detail="Failed to generate unique coupon codes")

            db.add_all(created)
            try:
                db.commit()
            except Exception as exc:
                db.rollback()
                # Likely unique constraint collisions. Let caller retry.
                raise HTTPException(status_code=500, detail=f"Failed to create batch: {exc}") from exc

        return CouponBatchCreateResponse(batch_id=batch_id, quantity=form.quantity, created_at=now)

    def list_coupons(
        self,
        *,
        channel: Optional[str] = None,
        status: Optional[str] = None,
        q: Optional[str] = None,
        expires_from: Optional[int] = None,
        expires_to: Optional[int] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[int, List[CouponData]]:
        now = _now()
        expires_from = normalize_optional_timestamp(expires_from)
        expires_to = normalize_optional_timestamp(expires_to)

        with _schema_aware_db() as db:
            query = db.query(Coupon)
            if channel:
                query = query.filter(Coupon.channel.contains(channel))
            if status:
                query = query.filter(Coupon.status == status)
            if q:
                query = query.filter(Coupon.code.contains(q))
            if expires_from:
                query = query.filter(Coupon.expires_at >= expires_from)
            if expires_to:
                query = query.filter(Coupon.expires_at <= expires_to)

            total = query.count()
            rows = (
                query.order_by(Coupon.created_at.desc())
                .offset(offset)
                .limit(limit)
                .all()
            )

        # Compute "EXPIRED" on read for display, without persisting state.
        items: List[CouponData] = []
        for row in rows:
            data = CouponData.model_validate(row)
            if data.status == CouponStatus.UNUSED.value and data.expires_at and now > data.expires_at:
                data.status = "EXPIRED"
            items.append(data)
        return total, items

    def lookup_by_code(self, *, code: str) -> Optional[CouponData]:
        with _schema_aware_db() as db:
            row = db.query(Coupon).filter(Coupon.code == code.strip()).first()
            return CouponData.model_validate(row) if row else None

    def update_coupon(
        self,
        *,
        coupon_id: str,
        form: CouponUpdateForm,
    ) -> Optional[CouponData]:
        now = _now()
        with _schema_aware_db() as db:
            row = db.query(Coupon).filter(Coupon.id == coupon_id).first()
            if not row:
                return None

            expired = bool(row.expires_at and now > int(row.expires_at))
            if row.status != CouponStatus.UNUSED.value or expired:
                raise HTTPException(status_code=409, detail="Coupon is not editable")

            update: Dict[str, object] = {"updated_at": now}
            if form.channel is not None:
                update["channel"] = form.channel
            if form.face_value is not None:
                update["face_value"] = form.face_value
            if form.valid_from is not None:
                update["valid_from"] = form.valid_from
            if form.expires_at is not None:
                update["expires_at"] = form.expires_at
            if form.remark is not None:
                # remark is stored on batch; keep on coupon destroy_reason? We don't have remark column for coupon.
                # Preserve for compatibility: no-op.
                pass

            db.query(Coupon).filter(Coupon.id == coupon_id).update(update, synchronize_session=False)
            db.commit()

            row = db.query(Coupon).filter(Coupon.id == coupon_id).first()
            return CouponData.model_validate(row) if row else None

    def destroy_coupon(
        self,
        *,
        coupon_id: str,
        destroyed_by_user_id: Optional[str],
        reason: str,
    ) -> bool:
        now = _now()
        with _schema_aware_db() as db:
            row = db.query(Coupon).filter(Coupon.id == coupon_id).first()
            if not row:
                return False
            if row.status == CouponStatus.USED.value:
                raise HTTPException(status_code=409, detail="Coupon already used")
            if row.status == CouponStatus.DESTROYED.value:
                return True

            db.query(Coupon).filter(Coupon.id == coupon_id).update(
                {
                    "status": CouponStatus.DESTROYED.value,
                    "destroyed_by_user_id": destroyed_by_user_id,
                    "destroyed_at": now,
                    "destroy_reason": reason,
                    "updated_at": now,
                },
                synchronize_session=False,
            )
            db.commit()
        return True

    def redeem(
        self,
        *,
        user_id: str,
        codes: Sequence[str],
        client_ip: Optional[str] = None,
    ) -> CouponRedeemResponse:
        if not codes:
            raise HTTPException(status_code=400, detail="No coupon codes provided")

        now = _now()
        dialect_name = None

        with _schema_aware_db() as db:
            dialect_name = db.get_bind().dialect.name.lower() if db.get_bind() else None

            # Lock coupons to avoid double-spend when supported.
            query = db.query(Coupon).filter(Coupon.code.in_(list(codes)))
            if dialect_name and dialect_name != "sqlite":
                query = query.with_for_update()
            rows: List[Coupon] = query.all()
            by_code: Dict[str, Coupon] = {r.code: r for r in rows}

            # Resolve which credit row to update (company credit owner is possible).
            resolved_user_id, resolved_company_id = Credits._resolve_credit_owner(user_id=user_id, company_id=None)

            credit_row: Optional[Credit] = None
            if resolved_company_id:
                credit_row = db.query(Credit).filter(Credit.company_id == resolved_company_id).first()
            else:
                credit_row = db.query(Credit).filter(Credit.user_id == resolved_user_id).first()

            if not credit_row:
                credit_row = Credit(
                    id=uuid.uuid4().hex,
                    user_id=resolved_user_id,
                    company_id=resolved_company_id,
                    credit=Decimal(CREDIT_DEFAULT_CREDIT.value),
                    created_at=now,
                    updated_at=now,
                )
                db.add(credit_row)
                db.flush()

            balance_before = Decimal(str(getattr(credit_row, "credit", None) or 0))

            items: List[CouponRedeemItem] = []
            total_added = Decimal("0")
            success_count = 0
            failed_count = 0

            for code in codes:
                row = by_code.get(code)
                decision = self._decide_redeem(row=row, now=now)
                if decision.status == "REDEEMED":
                    assert row is not None
                    success_count += 1
                    total_added += Decimal(str(row.face_value))
                    items.append(CouponRedeemItem(code=code, status="REDEEMED", face_value=Decimal(str(row.face_value))))
                    db.query(Coupon).filter(Coupon.id == row.id).update(
                        {
                            "status": CouponStatus.USED.value,
                            "used_by_user_id": user_id,
                            "used_at": now,
                            "updated_at": now,
                        },
                        synchronize_session=False,
                    )
                else:
                    failed_count += 1
                    items.append(CouponRedeemItem(code=code, status="FAILED", reason=decision.reason))

            if total_added > 0:
                balance_after = balance_before + total_added
                # Credit log aligns with existing CreditLog schema.
                log_entry = CreditLogModel(
                    user_id=resolved_user_id,
                    company_id=resolved_company_id,
                    credit=balance_after,
                    detail=SetCreditFormDetail(
                        api_path="/api/v1/billing/coupons/redeem",
                        api_params={"count": len(codes)},
                        desc="coupon redeem",
                    ).model_dump(),
                    created_at=now,
                )
                db.add(CreditLog(**log_entry.model_dump()))
                db.query(Credit).filter(Credit.id == credit_row.id).update(
                    {"credit": func.coalesce(Credit.credit, 0) + total_added, "updated_at": now},
                    synchronize_session=False,
                )
                # Best-effort: write into admin DB company credit logs for backend visibility.
                _log_admin_company_credit_change(
                    company_id=resolved_company_id,
                    balance_before=balance_before,
                    balance_after=balance_after,
                    user_id=str(user_id),
                )

            txn = CouponRedeemTxn(
                id=uuid.uuid4().hex,
                user_id=user_id,
                total_face_value=total_added,
                total_count=len(codes),
                success_count=success_count,
                failed_count=failed_count,
                request_fingerprint=_fingerprint(user_id, codes),
                client_ip=client_ip,
                created_at=now,
            )
            db.add(txn)
            db.commit()

            # Refresh credit for response
            refreshed_credit = Credits.init_credit(user_id=user_id, company_id=None)
            balance_after = refreshed_credit.credit

        return CouponRedeemResponse(
            success=True,
            user_id=user_id,
            total_submitted=len(codes),
            total_deduped=len(codes),
            total_redeemed=success_count,
            total_failed=failed_count,
            total_added_credit=total_added,
            credit_balance_after=balance_after,
            items=items,
        )

    @staticmethod
    def _decide_redeem(*, row: Optional[Coupon], now: int) -> RedeemDecision:
        if not row:
            return RedeemDecision(status="FAILED", reason="NOT_FOUND")
        if row.status == CouponStatus.DESTROYED.value:
            return RedeemDecision(status="FAILED", reason="DESTROYED")
        if row.status == CouponStatus.USED.value:
            return RedeemDecision(status="FAILED", reason="USED")
        # valid_from / expires_at guard
        if row.valid_from and now < int(row.valid_from):
            return RedeemDecision(status="FAILED", reason="NOT_YET_VALID")
        if row.expires_at and now > int(row.expires_at):
            return RedeemDecision(status="FAILED", reason="EXPIRED")
        return RedeemDecision(status="REDEEMED")


Coupons = CouponsTable()
