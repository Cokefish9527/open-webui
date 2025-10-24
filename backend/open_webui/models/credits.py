import time
import uuid
from decimal import Decimal
from typing import List, Optional, Tuple

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import JSON, BigInteger, Column, Numeric, String, ForeignKey

import importlib.util
import os

# 直接导入config.py文件
config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.py')
spec = importlib.util.spec_from_file_location("config", config_path)
config_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config_module)
CREDIT_EXCHANGE_RATIO = config_module.CREDIT_EXCHANGE_RATIO
from open_webui.internal.db import Base, get_db
from ._timestamp_utils import normalize_required_timestamp
from .hsai_companies import Companies
from .users import Users


####################
# User Credit DB Schema
####################


class Credit(Base):
    __tablename__ = "credit"

    id = Column(String, primary_key=True)
    user_id = Column(String, unique=True, nullable=False)
    company_id = Column(String, ForeignKey("companies.id"), nullable=True, index=True)
    credit = Column(Numeric(precision=24, scale=12))

    updated_at = Column(BigInteger)
    created_at = Column(BigInteger)


class CreditLog(Base):
    __tablename__ = "credit_log"

    id = Column(String, primary_key=True)
    user_id = Column(String, index=True, nullable=False)
    company_id = Column(String, ForeignKey("companies.id"), index=True, nullable=True)
    credit = Column(Numeric(precision=24, scale=12))
    detail = Column(JSON, nullable=True)

    created_at = Column(BigInteger, index=True)


class TradeTicket(Base):
    __tablename__ = "trade_ticket"

    id = Column(String, primary_key=True)
    user_id = Column(String, index=True, nullable=False)
    amount = Column(Numeric(precision=24, scale=12))
    detail = Column(JSON, nullable=True)

    created_at = Column(BigInteger, index=True)


####################
# Forms
####################


class CreditModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    user_id: str
    company_id: Optional[str] = None
    credit: Decimal = Field(default_factory=lambda: Decimal("0"))
    updated_at: int = Field(default_factory=lambda: int(time.time()))
    created_at: int = Field(default_factory=lambda: int(time.time()))

    @classmethod
    def _to_epoch(cls, value):
        from datetime import datetime
        if isinstance(value, datetime):
            return int(value.timestamp())
        return value

    @classmethod
    def model_validate(cls, value, *args, **kwargs):
        if value is None:
            return super().model_validate(value, *args, **kwargs)
        if isinstance(value, dict):
            data = dict(value)
        else:
            data = {
                "id": getattr(value, "id", None),
                "user_id": getattr(value, "user_id", None),
                "company_id": getattr(value, "company_id", None),
                "credit": getattr(value, "credit", None),
                "updated_at": getattr(value, "updated_at", None),
                "created_at": getattr(value, "created_at", None),
            }
        data["updated_at"] = cls._to_epoch(data.get("updated_at"))
        data["created_at"] = cls._to_epoch(data.get("created_at"))
        return super().model_validate(data, *args, **kwargs)


class CreditLogModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    user_id: str
    company_id: Optional[str] = None
    credit: Decimal = Field(default_factory=lambda: Decimal("0"))
    detail: dict = Field(default_factory=lambda: {})
    created_at: int = Field(default_factory=lambda: int(time.time()))


    @field_validator("created_at", mode="before")
    @classmethod
    def validate_credit_log_timestamps(cls, value):
        if value is None:
            raise ValueError("Timestamp value cannot be None")
        try:
            return normalize_required_timestamp(value)
        except ValueError as exc:
            raise ValueError(f"Invalid timestamp value: {exc}") from exc


class CreditLogUsage(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="allow")
    total_price: Optional[Decimal] = None
    prompt_unit_price: Optional[Decimal] = None
    completion_unit_price: Optional[Decimal] = None
    request_unit_price: Optional[Decimal] = None
    feature_price: Optional[Decimal] = None
    completion_tokens: Optional[int] = None
    prompt_tokens: Optional[int] = None
    total_tokens: Optional[int] = None


class SimpleModelModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: Optional[str] = None
    name: Optional[str] = None


class CreditLogSimpleDetailAPIParams(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    model: SimpleModelModel = Field(default_factory=lambda: {})


class CreditLogSimpleDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    desc: str = Field(default_factory=lambda: "")
    api_params: CreditLogSimpleDetailAPIParams = Field(default_factory=lambda: {})
    usage: CreditLogUsage = Field(default_factory=lambda: {})


class CreditLogSimpleModel(CreditLogModel):
    model_config = ConfigDict(from_attributes=True)
    detail: CreditLogSimpleDetail
    username: Optional[str] = Field(default="")


class SetCreditFormDetail(BaseModel):
    api_path: str = Field(default="")
    api_params: dict = Field(default_factory=lambda: {})
    desc: str = Field(default="")
    usage: dict = Field(default_factory=lambda: {})


class AddCreditForm(BaseModel):
    user_id: str
    company_id: Optional[str] = None
    amount: Decimal
    detail: SetCreditFormDetail


class SetCreditForm(BaseModel):
    user_id: str
    company_id: Optional[str] = None
    credit: Decimal
    detail: SetCreditFormDetail


class TradeTicketModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    user_id: str
    amount: Decimal = Field(default_factory=lambda: Decimal("0"))
    detail: dict = Field(default_factory=lambda: {})
    created_at: int = Field(default_factory=lambda: int(time.time()))


####################
# Tables
####################


class CreditsTable:
    def _resolve_credit_owner(
        self, user_id: Optional[str] = None, company_id: Optional[str] = None
    ) -> Tuple[str, Optional[str]]:
        resolved_user_id = user_id
        resolved_company_id = company_id

        if resolved_company_id is None and resolved_user_id:
            user = Users.get_user_by_id(resolved_user_id)
            if user and getattr(user, "company_id", None):
                resolved_company_id = user.company_id
                resolved_user_id = user.id

        if resolved_company_id:
            company = Companies.get_company_by_id(resolved_company_id)
            if company and getattr(company, "owner_user_id", None):
                resolved_user_id = company.owner_user_id
                resolved_company_id = company.id

        if resolved_user_id is None:
            raise HTTPException(
                status_code=400, detail="Unable to resolve company credit owner"
            )

        return resolved_user_id, resolved_company_id

    def insert_new_credit(
        self, user_id: str, company_id: Optional[str] = None
    ) -> Optional[CreditModel]:
        from open_webui.config import CREDIT_DEFAULT_CREDIT

        try:
            resolved_user_id, resolved_company_id = self._resolve_credit_owner(
                user_id=user_id, company_id=company_id
            )
            credit_model = CreditModel(
                user_id=resolved_user_id,
                company_id=resolved_company_id,
                credit=Decimal(CREDIT_DEFAULT_CREDIT.value),
            )
            with get_db() as db:
                result = Credit(**credit_model.model_dump())
                db.add(result)
                db.commit()
                db.refresh(result)
                if credit_model:
                    return credit_model
                return None
        except Exception:
            return None

    def init_credit(
        self, user_id: Optional[str], company_id: Optional[str]
    ) -> CreditModel:
        resolved_user_id, resolved_company_id = self._resolve_credit_owner(
            user_id=user_id, company_id=company_id
        )
        credit_model: Optional[CreditModel]
        if resolved_company_id:
            credit_model = self.get_credit_by_company_id(resolved_company_id)
        else:
            credit_model = self.get_credit_by_user_id(resolved_user_id)

        if credit_model is None:
            credit_model = self.insert_new_credit(
                user_id=resolved_user_id, company_id=resolved_company_id
            )

        if credit_model is not None:
            return credit_model

        raise HTTPException(status_code=500, detail="credit initialize failed")

    def init_credit_by_user_id(self, user_id: str) -> CreditModel:
        return self.init_credit(user_id=user_id, company_id=None)

    def init_credit_by_company_id(
        self, company_id: str, fallback_user_id: Optional[str] = None
    ) -> CreditModel:
        return self.init_credit(user_id=fallback_user_id, company_id=company_id)

    def get_credit_by_user_id(self, user_id: str) -> Optional[CreditModel]:
        resolved_user_id, resolved_company_id = self._resolve_credit_owner(
            user_id=user_id
        )
        if resolved_company_id:
            credit = self.get_credit_by_company_id(resolved_company_id)
            if credit:
                return credit
        try:
            with get_db() as db:
                credit = (
                    db.query(Credit)
                    .filter(Credit.user_id == resolved_user_id)
                    .first()
                )
                return CreditModel.model_validate(credit)
        except Exception:
            return None

    def get_credit_by_company_id(self, company_id: Optional[str]) -> Optional[CreditModel]:
        if not company_id:
            return None
        try:
            with get_db() as db:
                credit = (
                    db.query(Credit)
                    .filter(Credit.company_id == company_id)
                    .first()
                )
                return CreditModel.model_validate(credit)
        except Exception:
            return None

    def list_credits_by_user_id(self, user_ids: List[str]) -> List[CreditModel]:
        try:
            with get_db() as db:
                credits = db.query(Credit).filter(Credit.user_id.in_(user_ids)).all()
                return [CreditModel.model_validate(credit) for credit in credits]
        except Exception:
            return []

    def set_credit_by_user_id(self, form_data: SetCreditForm) -> CreditModel:
        credit_model = self.init_credit(
            user_id=form_data.user_id, company_id=form_data.company_id
        )
        log = CreditLogModel(
            user_id=credit_model.user_id,
            company_id=credit_model.company_id,
            credit=form_data.credit,
            detail=form_data.detail.model_dump(),
        )
        with get_db() as db:
            db.add(CreditLog(**log.model_dump()))
            db.query(Credit).filter(Credit.id == credit_model.id).update(
                {
                    "credit": form_data.credit,
                    "updated_at": int(time.time()),
                },
                synchronize_session=False,
            )
            db.commit()
        return self.init_credit(
            user_id=credit_model.user_id, company_id=credit_model.company_id
        )

    def add_credit_by_user_id(self, form_data: AddCreditForm) -> Optional[CreditModel]:
        credit_model = self.init_credit(
            user_id=form_data.user_id, company_id=form_data.company_id
        )
        log = CreditLogModel(
            user_id=credit_model.user_id,
            company_id=credit_model.company_id,
            credit=credit_model.credit + form_data.amount,
            detail=form_data.detail.model_dump(),
        )
        with get_db() as db:
            db.add(CreditLog(**log.model_dump()))
            db.query(Credit).filter(Credit.id == credit_model.id).update(
                {
                    "credit": Credit.credit + form_data.amount,
                    "updated_at": int(time.time()),
                },
                synchronize_session=False,
            )
            db.commit()
        return self.init_credit(
            user_id=credit_model.user_id, company_id=credit_model.company_id
        )


Credits = CreditsTable()


class TradeTicketTable:
    def insert_new_ticket(
        self, id: str, user_id: str, amount: float, detail: dict
    ) -> TradeTicketModel:
        try:
            ticket = TradeTicketModel(
                id=id,
                user_id=user_id,
                amount=Decimal(amount),
                detail=detail,
            )
            with get_db() as db:
                db.add(TradeTicket(**ticket.model_dump()))
                db.commit()
            return ticket
        except Exception as err:
            raise HTTPException(status_code=500, detail=str(err))

    def get_ticket_by_id(self, id: str) -> Optional[TradeTicketModel]:
        try:
            with get_db() as db:
                ticket = db.query(TradeTicket).filter(TradeTicket.id == id).first()
                return TradeTicketModel.model_validate(ticket)
        except Exception:
            return None

    def get_ticket_by_time(
        self, start_time: int, end_time: int
    ) -> List[TradeTicketModel]:
        try:
            with get_db() as db:
                logs = (
                    db.query(TradeTicket)
                    .filter(TradeTicket.created_at >= start_time)
                    .filter(TradeTicket.created_at < end_time)
                    .order_by(TradeTicket.created_at.asc())
                )
                return [TradeTicketModel.model_validate(log) for log in logs]
        except Exception:
            return []

    def update_credit_by_id(self, id: str, detail: dict) -> None:
        try:
            with get_db() as db:
                db.query(TradeTicket).filter(TradeTicket.id == id).update(
                    {"detail": detail}
                )
                db.commit()
                ticket = self.get_ticket_by_id(id)
                if ticket:
                    user = Users.get_user_by_id(ticket.user_id)
                    company_id = getattr(user, "company_id", None) if user else None
                    Credits.add_credit_by_user_id(
                        AddCreditForm(
                            user_id=ticket.user_id,
                            company_id=company_id,
                            amount=ticket.amount * Decimal(
                                CREDIT_EXCHANGE_RATIO.value
                            ),
                            detail=SetCreditFormDetail(desc="payment success"),
                        )
                    )
                return None
        except Exception:
            return None


TradeTickets = TradeTicketTable()


class CreditLogTable:
    def count_credit_log(
        self, user_ids: List[str] = None, company_id: Optional[str] = None
    ) -> int:
        with get_db() as db:
            query = db.query(CreditLog).order_by(CreditLog.created_at.desc())
            if user_ids:
                query = query.filter(CreditLog.user_id.in_(user_ids))
            if company_id:
                query = query.filter(CreditLog.company_id == company_id)
            return query.count()

    def get_credit_log_by_page(
        self,
        user_ids: List[str] = None,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
        company_id: Optional[str] = None,
    ) -> List[CreditLogSimpleModel]:
        with get_db() as db:
            query = db.query(CreditLog).order_by(CreditLog.created_at.desc())
            if user_ids:
                query = query.filter(CreditLog.user_id.in_(user_ids))
            if company_id:
                query = query.filter(CreditLog.company_id == company_id)
            if offset:
                query = query.offset(offset)
            if limit:
                query = query.limit(limit)
            all_logs = query.all()
            return [CreditLogSimpleModel.model_validate(log) for log in all_logs]

    def get_log_by_time(
        self, start_time: int, end_time: int
    ) -> List[CreditLogSimpleModel]:
        try:
            with get_db() as db:
                logs = (
                    db.query(CreditLog)
                    .filter(CreditLog.created_at >= start_time)
                    .filter(CreditLog.created_at < end_time)
                    .order_by(CreditLog.created_at.asc())
                )
                return [CreditLogSimpleModel.model_validate(log) for log in logs]
        except Exception:
            return []


CreditLogs = CreditLogTable()
