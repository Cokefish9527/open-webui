"""
Simple smoke-test script for HSAI prefixed endpoints.

Run with:
    python tool/test_hsai_endpoints.py --base-url http://localhost:8080/api/v1 --token sk-xxxx
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from typing import Dict, List, Optional

import requests


@dataclass
class Endpoint:
    method: str
    path: str
    params: Optional[Dict[str, str]] = None
    description: Optional[str] = None


DEFAULT_ENDPOINTS: List[Endpoint] = [
    Endpoint("GET", "/hsai/materials/", {"pi": "1", "ps": "5"}, "List materials"),
    Endpoint("GET", "/hsai/materials/folders", None, "List material folders"),
    Endpoint("GET", "/hsai/materials/statistics", None, "Material statistics"),
    Endpoint("GET", "/hsai/materials/categories", {"pi": "1", "ps": "10"}, "Material categories"),
    Endpoint("GET", "/hsai/materials/logs", {"pi": "1", "ps": "10"}, "Material file operation logs"),
    Endpoint("GET", "/hsai/materials/recovery/list", {"pi": "1", "ps": "5"}, "Material recycle bin listing"),
    Endpoint("GET", "/hsai/tasks/", {"pi": "1", "ps": "5"}, "List tasks"),
    Endpoint("GET", "/hsai/tasks/statistics", None, "Task statistics"),
    Endpoint("GET", "/hsai/dashboard/overview", None, "Dashboard overview"),
    Endpoint("GET", "/hsai/dashboard/kpi", None, "Dashboard KPI"),
    Endpoint("GET", "/hsai/dashboard/recent-activities", {"limit": "10"}, "Recent activities"),
    Endpoint("GET", "/hsai/dashboard/system-status", None, "System status"),
    Endpoint("GET", "/hsai/companies/", {"pi": "1", "ps": "5"}, "Company listing"),
    Endpoint("GET", "/hsai/projects/", {"pi": "1", "ps": "5"}, "Project listing"),
    Endpoint("GET", "/hsai/video-learning/videos", {"page": "1", "limit": "12", "status_filter": "all"}, "Pending videos"),
    Endpoint("GET", "/hsai/chat/statistics", None, "Chat statistics"),
    Endpoint("GET", "/hsai/chat/sessions", None, "Chat sessions"),
    Endpoint("GET", "/hsai/woc/status", None, "WOC status"),
    Endpoint("GET", "/hsai/woc/health", None, "WOC health probe"),
]


def build_headers(token: Optional[str]) -> Dict[str, str]:
    headers: Dict[str, str] = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def run_tests(
    base_url: str,
    token: Optional[str],
    endpoints: List[Endpoint],
    timeout: float,
) -> int:
    headers = build_headers(token)
    failures: List[str] = []

    for endpoint in endpoints:
        url = base_url.rstrip("/") + endpoint.path
        label = endpoint.description or endpoint.path
        try:
            response = requests.request(
                endpoint.method,
                url,
                headers=headers,
                params=endpoint.params,
                timeout=timeout,
            )
            status_ok = 200 <= response.status_code < 300
            summary = f"{endpoint.method} {endpoint.path}"
            if endpoint.params:
                summary += f" params={endpoint.params}"
            if status_ok:
                print(f"[OK] {summary} -> {response.status_code}")
            else:
                body_preview = response.text[:200].replace("\n", " ")
                print(f"[FAIL] {summary} -> {response.status_code} | {body_preview}")
                failures.append(f"{label} ({endpoint.method} {endpoint.path}) returned {response.status_code}")
        except Exception as exc:
            print(f"[ERROR] {endpoint.method} {endpoint.path} -> {exc}")
            failures.append(f"{label} raised {exc}")

    if failures:
        print("\nFailed endpoints:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("\nAll endpoints responded with 2xx status codes.")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Smoke test for HSAI endpoints.")
    parser.add_argument(
        "--base-url",
        default=os.environ.get("HSAI_BASE_URL", "http://localhost:8080/api/v1"),
        help="API base URL (default: %(default)s or env HSAI_BASE_URL)",
    )
    parser.add_argument(
        "--token",
        default=os.environ.get("HSAI_BEARER_TOKEN"),
        help="Bearer token for Authorization header (default: env HSAI_BEARER_TOKEN)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=float(os.environ.get("HSAI_TEST_TIMEOUT", "10")),
        help="HTTP timeout in seconds (default: %(default)s)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    return run_tests(
        base_url=args.base_url,
        token=args.token,
        endpoints=DEFAULT_ENDPOINTS,
        timeout=args.timeout,
    )


if __name__ == "__main__":
    sys.exit(main())
