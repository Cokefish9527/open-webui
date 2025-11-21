#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
站点镜像抓取工具（增量）

用途：抓取同站点（同协议+域名）的页面与静态资源，将未保存到本地的页面增量保存到指定目录。

特性：
- 同站点范围限制（scheme+host 必须与 base 一致）
- 增量模式：已存在的文件将跳过
- 简单链接发现：a[href]、link[href]、script[src]、img[src]
- 令牌支持：可设置 X-Ops-Dashboard-Token 或 Authorization: Bearer
- 可选抓取静态资源（/static/*）

示例：
  python open-webui/tool/site_mirror.py \
    --base http://192.168.20.32:5000 \
    --out open-webui/data/site_mirror \
    --start / /system/index/ops_dashboard \
    --include-static \
    --max-pages 500 \
    --concurrency 8 \
    --token header:X-Ops-Dashboard-Token=unit-test-token

注意：脚本仅抓取公开可访问或携带正确令牌可访问的页面；请遵守目标站点的访问策略与法律合规要求。
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import queue
import re
import sys
import threading
import time
from pathlib import Path
from typing import Iterable, Optional, Set, Tuple
from urllib.parse import urljoin, urlparse

try:
    import requests
except Exception as e:  # pragma: no cover
    print("[site_mirror] 需要安装 requests 库: pip install requests", file=sys.stderr)
    raise


HREF_RE = re.compile(r"href=[\"']([^\"'#>]+)")
SRC_RE = re.compile(r"src=[\"']([^\"'#>]+)")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Mirror same-site pages incrementally")
    p.add_argument("--base", required=True, help="基地址，如 http://host:5000")
    p.add_argument("--out", default="open-webui/data/site_mirror", help="输出根目录")
    p.add_argument("--start", nargs="*", default=["/"], help="起始路径列表（相对 base）")
    p.add_argument("--include-static", action="store_true", help="抓取 /static/* 资源")
    p.add_argument("--max-pages", type=int, default=500, help="最多抓取的页面数量（HTML 页）")
    p.add_argument("--concurrency", type=int, default=6, help="并发下载线程数")
    p.add_argument("--delay", type=float, default=0.0, help="每次请求后的延迟(秒)")
    p.add_argument(
        "--token",
        default=None,
        help="可选令牌，格式：'header:X-Ops-Dashboard-Token=xxx' 或 'bearer:xxx'",
    )
    return p.parse_args()


def make_headers(token: Optional[str]) -> dict:
    headers = {"User-Agent": "SiteMirror/1.0"}
    if not token:
        return headers
    t = token.strip()
    if t.lower().startswith("header:"):
        try:
            kv = t.split(":", 1)[1]
            k, v = kv.split("=", 1)
            headers[k.strip()] = v.strip()
        except Exception:
            pass
    elif t.lower().startswith("bearer:"):
        headers["Authorization"] = f"Bearer {t.split(':',1)[1].strip()}"
    return headers


def ensure_dir(p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)


def safe_name_from_url_path(path: str, query: str) -> str:
    if not path or path.endswith("/"):
        return os.path.join(path.lstrip("/"), "index.html")
    # 保留原始扩展名；若无扩展名且存在查询参数则使用哈希
    suffix = Path(path).suffix
    if query:
        digest = hashlib.sha1(query.encode("utf-8")).hexdigest()[:12]
        if suffix:
            base = path[:-len(suffix)]
            return f"{base}__q_{digest}{suffix}"
        return f"{path}__q_{digest}.html"
    return path.lstrip("/")


def same_site(url: str, base: str) -> bool:
    u, b = urlparse(url), urlparse(base)
    return (u.scheme, u.netloc) == (b.scheme, b.netloc)


def is_probably_html(resp: requests.Response) -> bool:
    ctype = (resp.headers.get("Content-Type") or "").lower()
    return ctype.startswith("text/html") or ctype.startswith("application/xhtml")


def extract_links(html_bytes: bytes) -> Set[str]:
    text = html_bytes.decode("utf-8", errors="ignore")
    links = set()
    links.update(HREF_RE.findall(text))
    links.update(SRC_RE.findall(text))
    return links


class Mirror:
    def __init__(self, base: str, out_root: Path, include_static: bool, headers: dict, max_pages: int, delay: float) -> None:
        self.base = base.rstrip("/")
        self.parsed = urlparse(self.base)
        # Windows 路径不允许 ':'，将端口等特殊字符替换为 '_'
        safe_netloc = re.sub(r"[^A-Za-z0-9_.-]", "_", self.parsed.netloc)
        self.out_root = out_root / safe_netloc
        self.include_static = include_static
        self.headers = headers
        self.max_pages = max_pages
        self.delay = delay

        self.visited_pages: Set[str] = set()
        self.saved_files: Set[str] = set()
        self.lock = threading.Lock()
        self.session = requests.Session()

        # 恢复已抓取索引
        self.index_path = self.out_root / ".mirror_index.json"
        if self.index_path.exists():
            try:
                data = json.loads(self.index_path.read_text(encoding="utf-8"))
                self.visited_pages = set(data.get("visited_pages", []))
                self.saved_files = set(data.get("saved_files", []))
            except Exception:
                pass

    def _persist_index(self) -> None:
        self.out_root.mkdir(parents=True, exist_ok=True)
        data = {
            "visited_pages": sorted(self.visited_pages),
            "saved_files": sorted(self.saved_files),
            "base": self.base,
        }
        self.index_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _in_scope(self, url: str) -> bool:
        if not same_site(url, self.base):
            return False
        if not self.include_static:
            # 排除静态资源，仅抓 HTML 页面
            p = urlparse(url).path or ""
            if p.startswith("/static/"):
                return False
        return True

    def _target_file(self, url: str) -> Path:
        u = urlparse(url)
        rel = safe_name_from_url_path(u.path or "/", u.query or "")
        return self.out_root / rel.lstrip("/")

    def _already_saved(self, url: str) -> bool:
        p = self._target_file(url)
        return p.exists()

    def _save(self, url: str, content: bytes) -> None:
        p = self._target_file(url)
        ensure_dir(p)
        p.write_bytes(content)
        with self.lock:
            self.saved_files.add(str(p))

    def fetch(self, url: str) -> Tuple[Optional[bytes], Optional[requests.Response]]:
        try:
            resp = self.session.get(url, headers=self.headers, timeout=15)
            if self.delay:
                time.sleep(self.delay)
            if resp.status_code >= 400:
                return None, resp
            return resp.content, resp
        except Exception:
            return None, None

    def crawl(self, starts: Iterable[str], concurrency: int = 6) -> None:
        q: "queue.Queue[str]" = queue.Queue()
        for s in starts:
            q.put(urljoin(self.base + "/", s))

        def worker():
            while True:
                try:
                    u = q.get_nowait()
                except queue.Empty:
                    return
                if not self._in_scope(u):
                    q.task_done(); continue
                with self.lock:
                    if u in self.visited_pages or len(self.visited_pages) >= self.max_pages:
                        q.task_done(); continue
                    self.visited_pages.add(u)

                # 若目标文件已存在且为 HTML 页面，仍可读取并抽取链接（避免遗漏）
                if self._already_saved(u):
                    # 尝试从本地文件抽取链接
                    try:
                        local_bytes = self._target_file(u).read_bytes()
                        for link in extract_links(local_bytes):
                            absu = urljoin(u, link)
                            if self._in_scope(absu):
                                q.put(absu)
                    except Exception:
                        pass
                    q.task_done(); continue

                body, resp = self.fetch(u)
                if body is None:
                    q.task_done(); continue

                # 保存到本地
                self._save(u, body)

                # 若为 HTML，抽取更多链接
                if resp is not None and is_probably_html(resp):
                    for link in extract_links(body):
                        absu = urljoin(u, link)
                        if self._in_scope(absu):
                            q.put(absu)
                q.task_done()

        # 并发启动
        threads = [threading.Thread(target=worker, daemon=True) for _ in range(max(1, concurrency))]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self._persist_index()


def main() -> None:
    args = parse_args()
    headers = make_headers(args.token)
    out_root = Path(args.out)
    mirror = Mirror(
        base=args.base,
        out_root=out_root,
        include_static=args.include_static,
        headers=headers,
        max_pages=args.max_pages,
        delay=args.delay,
    )
    mirror.crawl(args.start, concurrency=args.concurrency)
    print(f"[site_mirror] done. index={mirror.index_path}")


if __name__ == "__main__":
    main()
