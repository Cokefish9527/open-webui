#!/usr/bin/env python3
"""Ensure tenant and automation accounts exist for Playwright E2E."""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import requests

DEFAULT_ACCOUNTS = [f"test{str(i).zfill(3)}@hsai.cc" for i in range(1, 11)]
DEFAULT_TENANT = "福州华商时代自动化测试"
DEFAULT_PASSWORD = os.environ.get("E2E_TEST_ACCOUNT_PASSWORD", "H@SaiAutoTest2025!")
DEFAULT_BASE_URL = os.environ.get("EXTERNAL_ADMIN_BASE_URL", "http://localhost:8080/api/v1/external/admin")
DEFAULT_TOKEN = os.environ.get("EXTERNAL_ADMIN_TOKEN")


class ExternalAdminClient:
    def __init__(self, base_url: str, token: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        )

    def request(self, method: str, path: str, *, params: Optional[dict] = None, json_body: Optional[dict] = None) -> requests.Response:
        url = f"{self.base_url}{path}"
        response = self.session.request(method, url, params=params, json=json_body, timeout=30)
        if response.status_code >= 400:
            raise RuntimeError(f"{method} {url} failed: {response.status_code} {response.text}")
        return response

    def list_companies(self, page_size: int = 100) -> List[dict]:
        response = self.request("GET", "/companies", params={"ps": page_size, "pi": 1})
        payload = response.json()
        return payload.get("data", [])

    def list_users(self, *, company_id: Optional[str], page_size: int = 200) -> List[dict]:
        page = 1
        users: List[dict] = []
        while True:
            params = {"page": page, "size": page_size}
            if company_id:
                params["company_id"] = company_id
            response = self.request("GET", "/users", params=params)
            payload = response.json()
            batch = payload.get("users", payload.get("data", []))
            if not isinstance(batch, list):
                break
            users.extend(batch)
            total = payload.get("total", len(users))
            if len(users) >= total:
                break
            page += 1
        return users

    def create_user(self, *, email: str, password: str, tenant: str) -> dict:
        payload = {
            "name": email.split("@")[0],
            "email": email,
            "password": password,
            "business_name": tenant,
            "role": "admin",
            "profile_image_url": "/user.png",
        }
        response = self.request("POST", "/users", json_body=payload)
        return response.json()


def find_company_id(client: ExternalAdminClient, tenant: str) -> Optional[str]:
    companies = client.list_companies()
    for company in companies:
        if company.get("name") == tenant:
            return company.get("id")
    return None


def ensure_accounts(client: ExternalAdminClient, tenant: str, accounts: List[str], password: str) -> Dict[str, str]:
    status: Dict[str, str] = {}
    company_id = find_company_id(client, tenant)

    for index, email in enumerate(accounts):
        exists = False
        search_company = company_id
        if not search_company and index == 0:
            # allow first account to bootstrap tenant even没有企业
            pass
        else:
            users = client.list_users(company_id=search_company)
            exists = any(user.get("email", "").lower() == email.lower() for user in users)

        if exists:
            status[email] = "existing"
            continue

        client.create_user(email=email, password=password, tenant=tenant)
        status[email] = "created"
        if not company_id:
            company_id = find_company_id(client, tenant)

    # 最后再扫描一次确保所有账号落在正确租户下
    if company_id:
        tenant_users = client.list_users(company_id=company_id)
        missing = [email for email in accounts if not any(user.get("email", "").lower() == email.lower() for user in tenant_users)]
        if missing:
            raise RuntimeError(f"账号 {missing} 未能创建成功，请检查 external_admin 日志。")
    else:
        raise RuntimeError("仍未找到租户，可能 external_admin 或 provisioning 配置异常。")

    return status


def write_report(report: dict, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare tenant + automation accounts for Playwright tests")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="external_admin API base, e.g. http://host:port/api/v1/external/admin")
    parser.add_argument("--token", default=DEFAULT_TOKEN, help="Bearer token for external_admin APIs")
    parser.add_argument("--tenant", default=os.environ.get("E2E_TENANT_NAME", DEFAULT_TENANT))
    parser.add_argument("--password", default=DEFAULT_PASSWORD, help="Password applied to created accounts")
    parser.add_argument("--accounts", nargs="*", default=None, help="Override default account pool")
    parser.add_argument("--report", default="tests/playwright/artifacts/setup/test_accounts_report.json")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.token:
        print("[prepare_test_accounts] 缺少 external_admin token (设置 EXTERNAL_ADMIN_TOKEN 或 --token)", file=sys.stderr)
        return 2

    accounts = args.accounts or DEFAULT_ACCOUNTS
    client = ExternalAdminClient(args.base_url, args.token)

    try:
        status = ensure_accounts(client, args.tenant, accounts, args.password)
    except Exception as exc:  # noqa: BLE001
        print(f"[prepare_test_accounts] 失败: {exc}", file=sys.stderr)
        return 1

    report = {
        "tenant": args.tenant,
        "accounts": status,
        "base_url": args.base_url,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    write_report(report, Path(args.report))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
