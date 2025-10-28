import json
import logging
import os
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from open_webui.env import SRC_LOG_LEVELS
from open_webui.internal.db import get_db
from open_webui.models.social_automation import (
    SocialAccount,
    SocialAccountModel,
    SocialAccountStatus,
    SocialAutomationRun,
    SocialAutomationRunModel,
    SocialCampaign,
    SocialCampaignModel,
    SocialPost,
    SocialPostModel,
    SocialPostStatus,
    SocialRunStatus,
)
from open_webui.utils.playwright_mcp_client import (
    PlaywrightMCPClient,
    PlaywrightMCPError,
    PlaywrightMCPResult,
)

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])


@contextmanager
def session_scope() -> Session:
    with get_db() as session:
        yield session


class PlaywrightMCPService:
    """Playwright MCP 社交账号自动化服务"""

    def __init__(self):
        self._client_cls = PlaywrightMCPClient
        self._credential_root = Path(
            os.getenv("PLAYWRIGHT_CREDENTIAL_ROOT", Path.cwd() / "playwright_credentials")
        ).resolve()
        self._profile_root = Path(
            os.getenv("PLAYWRIGHT_PROFILE_ROOT", Path.cwd() / "playwright_profiles")
        ).resolve()
        self._credential_root.mkdir(parents=True, exist_ok=True)
        (self._credential_root / "cookies").mkdir(parents=True, exist_ok=True)
        self._profile_root.mkdir(parents=True, exist_ok=True)

    # ---------
    # Account APIs
    # ---------

    def list_accounts(self, tenant_id: str) -> List[SocialAccountModel]:
        with session_scope() as session:
            accounts = (
                session.query(SocialAccount)
                .filter(SocialAccount.tenant_id == tenant_id)
                .order_by(SocialAccount.created_at.desc())
                .all()
            )
            return [SocialAccountModel.model_validate(acc) for acc in accounts]

    def get_account(self, account_id: str) -> Optional[SocialAccount]:
        with session_scope() as session:
            return (
                session.query(SocialAccount)
                .filter(SocialAccount.id == account_id)
                .first()
            )

    def create_account(
        self,
        tenant_id: str,
        platform: str,
        handle: str,
        display_name: Optional[str],
        encrypted_credentials_ref: Optional[str],
        playwright_profile_path: Optional[str],
        vpn_profile_id: Optional[str],
        created_by: str,
        auto_prepare: bool = True,
    ) -> SocialAccountModel:
        now = int(time.time())
        account_id = str(uuid.uuid4())

        credential_ref, profile_path, cookies_path = self._ensure_account_scaffold(
            tenant_id=tenant_id,
            account_id=account_id,
            handle=handle,
            provided_ref=encrypted_credentials_ref,
            provided_profile=playwright_profile_path,
        )

        with session_scope() as session:
            existing = (
                session.query(SocialAccount)
                .filter(
                    SocialAccount.tenant_id == tenant_id,
                    SocialAccount.platform == platform,
                    SocialAccount.handle == handle,
                )
                .first()
            )
            if existing:
                raise ValueError("账户已存在")

            account = SocialAccount(
                id=account_id,
                tenant_id=tenant_id,
                platform=platform,
                handle=handle,
                display_name=display_name,
                encrypted_credentials_ref=credential_ref,
                playwright_profile_path=profile_path,
                vpn_profile_id=vpn_profile_id or "",
                status=SocialAccountStatus.INACTIVE.value,
                created_by=created_by,
                created_at=now,
                updated_at=now,
            )
            session.add(account)
            session.commit()
            session.refresh(account)
            log.info("创建社媒账号 %s/%s (%s)", tenant_id, handle, account_id)
            self._log_account_scaffold(account, cookies_path)

            if auto_prepare and platform.lower() == "tiktok":
                log.info(
                    "账号 %s 已初始化，可调用 /social/accounts/%s/prepare 触发交互式登录流程",
                    account_id,
                    account_id,
                )

            return SocialAccountModel.model_validate(account)

    def mark_account_status(
        self, account_id: str, status: SocialAccountStatus
    ) -> Optional[SocialAccountModel]:
        with session_scope() as session:
            account = (
                session.query(SocialAccount)
                .filter(SocialAccount.id == account_id)
                .first()
            )
            if not account:
                return None
            account.status = status.value
            account.updated_at = int(time.time())
            session.commit()
            session.refresh(account)
            return SocialAccountModel.model_validate(account)

    # ---------
    # Campaign/Post APIs
    # ---------

    def create_campaign(
        self,
        tenant_id: str,
        name: str,
        description: Optional[str],
        schedule_strategy: Optional[str],
        created_by: str,
    ) -> SocialCampaignModel:
        now = int(time.time())
        with session_scope() as session:
            campaign = SocialCampaign(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                name=name,
                description=description,
                schedule_strategy=schedule_strategy,
                status="draft",
                created_by=created_by,
                created_at=now,
                updated_at=now,
            )
            session.add(campaign)
            session.commit()
            session.refresh(campaign)
            return SocialCampaignModel.model_validate(campaign)

    def create_post(
        self,
        tenant_id: str,
        account_id: str,
        created_by: str,
        title: Optional[str],
        caption: Optional[str],
        media_assets: Optional[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]],
        schedule_time: Optional[int],
        campaign_id: Optional[str] = None,
    ) -> SocialPostModel:
        now = int(time.time())
        with session_scope() as session:
            account = (
                session.query(SocialAccount)
                .filter(
                    SocialAccount.id == account_id,
                    SocialAccount.tenant_id == tenant_id,
                )
                .first()
            )
            if not account:
                raise ValueError("账号不存在或不属于当前租户")

            post = SocialPost(
                id=str(uuid.uuid4()),
                campaign_id=campaign_id,
                account_id=account_id,
                title=title,
                caption=caption,
                media_assets=media_assets or {},
                post_metadata=metadata or {},
                schedule_time=schedule_time,
                status=SocialPostStatus.PENDING_APPROVAL.value,
                created_by=created_by,
                created_at=now,
                updated_at=now,
            )
            session.add(post)
            session.commit()
            session.refresh(post)
            return SocialPostModel.model_validate(post)

    def list_posts(self, tenant_id: str, account_id: Optional[str] = None) -> List[SocialPostModel]:
        with session_scope() as session:
            query = (
                session.query(SocialPost)
                .join(SocialAccount, SocialPost.account_id == SocialAccount.id)
                .filter(SocialAccount.tenant_id == tenant_id)
            )
            if account_id:
                query = query.filter(SocialPost.account_id == account_id)

            posts = query.order_by(SocialPost.created_at.desc()).all()
            return [SocialPostModel.model_validate(post) for post in posts]

    # ---------
    # TikTok Automations
    # ---------

    async def ensure_tiktok_login(self, account_id: str, initiated_by: str) -> PlaywrightMCPResult:
        return await self.prepare_account(
            account_id=account_id,
            initiated_by=initiated_by,
            interactive=False,
        )

    async def fetch_tiktok_creator_info(
        self, account_id: str, target_handle: str, initiated_by: str
    ) -> PlaywrightMCPResult:
        return await self._execute_tool_for_account(
            account_id=account_id,
            tool_name="tiktok_fetch_creator",
            arguments={"target_handle": target_handle},
            trigger_source=f"creator_info:{initiated_by}",
        )

    async def fetch_tiktok_video_info(
        self, account_id: str, video_url: str, initiated_by: str
    ) -> PlaywrightMCPResult:
        return await self._execute_tool_for_account(
            account_id=account_id,
            tool_name="tiktok_fetch_video",
            arguments={"video_url": video_url},
            trigger_source=f"video_info:{initiated_by}",
        )

    async def publish_tiktok_video(
        self, post_id: str, initiated_by: str
    ) -> Tuple[SocialAutomationRunModel, PlaywrightMCPResult]:
        with session_scope() as session:
            post = session.query(SocialPost).filter(SocialPost.id == post_id).first()
            if not post:
                raise ValueError("发布任务不存在")
            account = session.query(SocialAccount).filter(SocialAccount.id == post.account_id).first()
            if not account:
                raise ValueError("关联账号不存在")
            post.status = SocialPostStatus.IN_PROGRESS.value
            post.updated_at = int(time.time())
            session.commit()

        result = await self._execute_tool_for_account(
            account_id=post.account_id,
            tool_name="tiktok_publish_video",
            arguments={
                "post_id": post_id,
                "title": post.title,
                "caption": post.caption,
                "media_assets": post.media_assets or {},
                "metadata": post.post_metadata or {},
            },
            trigger_source=f"publish:{initiated_by}",
            post_id=post_id,
        )

        with session_scope() as session:
            run = (
                session.query(SocialAutomationRun)
                .filter(
                    SocialAutomationRun.post_id == post_id,
                )
                .order_by(SocialAutomationRun.created_at.desc())
                .first()
            )
            if not run:
                raise ValueError("未找到发布执行记录")
            return (
                SocialAutomationRunModel.model_validate(run),
                result,
            )

    async def prepare_account(
        self,
        account_id: str,
        initiated_by: str,
        interactive: bool = True,
        interactive_timeout: Optional[int] = None,
    ) -> PlaywrightMCPResult:
        arguments: Dict[str, Any] = {"action": "ensure_login"}
        if interactive:
            arguments["interactive"] = True
            if interactive_timeout:
                arguments["interactive_timeout"] = interactive_timeout
        return await self._execute_tool_for_account(
            account_id=account_id,
            tool_name="tiktok_login",
            arguments=arguments,
            trigger_source=f"prepare:{initiated_by}",
        )

    # ---------
    # Internals
    # ---------

    async def _execute_tool_for_account(
        self,
        account_id: str,
        tool_name: str,
        arguments: Dict[str, Any],
        trigger_source: str,
        post_id: Optional[str] = None,
    ) -> PlaywrightMCPResult:
        with session_scope() as session:
            account = (
                session.query(SocialAccount)
                .filter(SocialAccount.id == account_id)
                .first()
            )
            if not account:
                raise ValueError("账号不存在")
            account_data = {
                "id": account.id,
                "tenant_id": account.tenant_id,
                "platform": account.platform,
                "handle": account.handle,
                "display_name": account.display_name,
                "encrypted_credentials_ref": account.encrypted_credentials_ref,
                "playwright_profile_path": account.playwright_profile_path,
                "vpn_profile_id": account.vpn_profile_id,
            }
            run = self._create_run_record(
                session=session,
                post_id=post_id,
                trigger_source=trigger_source,
            )
            session.flush()
            session.commit()

        metadata = {
            "tenant_id": account_data["tenant_id"],
            "account_id": account_id,
            "trigger_source": trigger_source,
            "run_id": run.id,
        }

        payload = {
            "account": {
                "id": account_data["id"],
                "tenant_id": account_data["tenant_id"],
                "platform": account_data["platform"],
                "handle": account_data["handle"],
                "display_name": account_data["display_name"],
                "encrypted_credentials_ref": account_data["encrypted_credentials_ref"],
                "playwright_profile_path": account_data["playwright_profile_path"],
                "vpn_profile_id": account_data["vpn_profile_id"],
            },
            "arguments": arguments,
        }

        if post_id:
            payload["post_id"] = post_id

        start_ts = time.time()
        try:
            async with self._client_cls() as client:
                result = await client.execute(tool_name, payload, metadata=metadata)
        except PlaywrightMCPError as exc:
            log.error("Playwright MCP 执行失败: %s", exc)
            self._finalize_run(
                run_id=run.id,
                status=SocialRunStatus.FAILED,
                error_reason=str(exc),
                artifacts=None,
                duration=int((time.time() - start_ts) * 1000),
                request_id=None,
            )
            if post_id:
                self._update_post_status(
                    post_id=post_id,
                    status=SocialPostStatus.FAILED,
            metadata={"error": str(exc)},
                )
            raise
        except Exception as exc:
            log.exception("Playwright MCP 未知异常: %s", exc)
            self._finalize_run(
                run_id=run.id,
                status=SocialRunStatus.FAILED,
                error_reason=str(exc),
                artifacts=None,
                duration=int((time.time() - start_ts) * 1000),
                request_id=None,
            )
            if post_id:
                self._update_post_status(
                    post_id=post_id,
                    status=SocialPostStatus.FAILED,
            metadata={"error": str(exc)},
                )
            raise

        self._finalize_run(
            run_id=run.id,
            status=SocialRunStatus.SUCCEEDED,
            artifacts=result.artifacts,
            error_reason=None,
            duration=int((time.time() - start_ts) * 1000),
            request_id=result.request_id,
        )

        if post_id:
            self._update_post_status(
                post_id=post_id,
                status=SocialPostStatus.PUBLISHED,
                metadata=result.artifacts,
            )
        elif tool_name == "tiktok_login":
            self.mark_account_status(account_id, SocialAccountStatus.ACTIVE)

        health_status = result.artifacts.get("health_status") if isinstance(result.artifacts, dict) else None
        if health_status:
            self._update_account_health(account_id, health_status)

        return result

    def _ensure_account_scaffold(
        self,
        tenant_id: str,
        account_id: str,
        handle: str,
        provided_ref: Optional[str],
        provided_profile: Optional[str],
    ) -> Tuple[str, str, Path]:
        slug_tenant = self._slug_segment(tenant_id)
        slug_handle = self._slug_segment(handle or account_id)

        credential_ref = provided_ref or f"{slug_tenant}_{slug_handle}"
        credential_file = (self._credential_root / f"{credential_ref}.json").resolve()
        credential_file.parent.mkdir(parents=True, exist_ok=True)

        cookies_path = (self._credential_root / "cookies" / f"{credential_ref}_cookies.json").resolve()
        cookies_path.parent.mkdir(parents=True, exist_ok=True)

        if not credential_file.exists():
            template = {
                "username": "",
                "password": "",
                "cookies_path": str(cookies_path),
                "notes": (
                    "填写用户名/密码可在脚本内自动登录；"
                    f"若选择人工配合，请调用 /social/accounts/{account_id}/prepare 完成交互式登录后，该文件会持续保存 Cookie。"
                ),
            }
            credential_file.write_text(json.dumps(template, indent=2, ensure_ascii=False), encoding="utf-8")

        if provided_profile:
            profile_path = Path(provided_profile).expanduser().resolve()
        else:
            profile_path = (self._profile_root / slug_tenant / slug_handle).resolve()
        profile_path.mkdir(parents=True, exist_ok=True)

        return credential_ref, str(profile_path), cookies_path

    def _log_account_scaffold(self, account: SocialAccount, cookies_path: Path) -> None:
        log.info(
            "账号 scaffold: credential_ref=%s (目录=%s), profile_path=%s, cookies_path=%s",
            account.encrypted_credentials_ref,
            self._credential_root,
            account.playwright_profile_path,
            cookies_path,
        )

    @staticmethod
    def _slug_segment(value: str) -> str:
        if not value:
            return "account"
        return "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in value.lower())

    def delete_account(self, tenant_id: str, account_id: str) -> bool:
        with session_scope() as session:
            account = (
                session.query(SocialAccount)
                .filter(SocialAccount.id == account_id, SocialAccount.tenant_id == tenant_id)
                .first()
            )
            if not account:
                return False

            credential_ref = account.encrypted_credentials_ref
            profile_path = account.playwright_profile_path

            posts = session.query(SocialPost).filter(SocialPost.account_id == account_id).all()
            for post in posts:
                session.delete(post)

            session.delete(account)
            session.commit()

        self._cleanup_account_files(credential_ref, profile_path)
        return True

    def _cleanup_account_files(self, credential_ref: Optional[str], profile_path: Optional[str]) -> None:
        if credential_ref:
            credential_file = (self._credential_root / f"{credential_ref}.json").resolve()
            cookies_file = (self._credential_root / "cookies" / f"{credential_ref}_cookies.json").resolve()
            for path in (credential_file, cookies_file):
                self._safe_remove_file(path)

        if profile_path:
            path_obj = Path(profile_path).expanduser().resolve()
            try:
                if path_obj.is_dir() and str(path_obj).startswith(str(self._profile_root)):
                    import shutil
                    shutil.rmtree(path_obj, ignore_errors=True)
            except Exception as exc:
                log.warning("删除浏览器配置目录失败: %s", exc)

    def _safe_remove_file(self, path: Path) -> None:
        try:
            if path.exists() and path.is_file() and str(path).startswith(str(self._credential_root)):
                path.unlink()
        except Exception as exc:
            log.warning("删除凭证文件失败: %s", exc)

    def _create_run_record(
        self,
        session: Session,
        trigger_source: str,
        post_id: Optional[str] = None,
    ) -> SocialAutomationRun:
        now = int(time.time())
        run = SocialAutomationRun(
            id=str(uuid.uuid4()),
            post_id=post_id,
            trigger_source=trigger_source,
            status=SocialRunStatus.RUNNING.value,
            created_at=now,
            updated_at=now,
        )
        session.add(run)
        return run

    def _finalize_run(
        self,
        run_id: str,
        status: SocialRunStatus,
        duration: Optional[int],
        artifacts: Optional[Dict[str, Any]],
        error_reason: Optional[str],
        request_id: Optional[str],
    ) -> None:
        with session_scope() as session:
            run = session.query(SocialAutomationRun).filter(SocialAutomationRun.id == run_id).first()
            if not run:
                log.warning("尝试更新不存在的运行记录: %s", run_id)
                return
            run.status = status.value
            run.duration_ms = duration
            run.updated_at = int(time.time())
            if request_id:
                run.mcp_request_id = request_id
            if artifacts:
                run.result_payload = artifacts
                run.screenshot_path = artifacts.get("screenshot_path")
                run.har_path = artifacts.get("har_path")
                run.proxy_exit_ip = artifacts.get("proxy_exit_ip")
            if error_reason:
                run.error_reason = error_reason
            session.commit()

    def _update_post_status(
        self,
        post_id: str,
        status: SocialPostStatus,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        with session_scope() as session:
            post = session.query(SocialPost).filter(SocialPost.id == post_id).first()
            if not post:
                log.warning("尝试更新不存在的内容任务: %s", post_id)
                return
            post.status = status.value
            post.updated_at = int(time.time())
            if metadata:
                merged = post.post_metadata if isinstance(post.post_metadata, dict) else {}
                merged.update({"publish_result": metadata})
                post.post_metadata = merged
            session.commit()

    def _update_account_health(self, account_id: str, health_status: str) -> None:
        with session_scope() as session:
            account = (
                session.query(SocialAccount)
                .filter(SocialAccount.id == account_id)
                .first()
            )
            if not account:
                return
            account.health_status = health_status
            account.updated_at = int(time.time())
            session.commit()


playwright_mcp_service = PlaywrightMCPService()

