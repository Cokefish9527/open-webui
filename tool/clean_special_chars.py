#!/usr/bin/env python3
"""
字符治理工具：扫描并修复文本文件中的 UTF-8 BOM 及不可见控制字符。

默认会递归遍历给定目录（仓库根目录），仅处理常见文本扩展名。
可使用 --extensions 指定扩展名集合（逗号分隔），或 --all 扫描全部文件。
提供 --check（默认）和 --fix 两种模式：
  * --check 发现异常时输出报告并返回退出码 1。
  * --fix   在内存中清理 BOM / 控制字符并写回文件，成功后退出码 0。

控制字符定义：ASCII < 32 的字符，排除常用换行符（CR、LF）与制表符（TAB）。
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence, Set, Tuple

BOM_BYTES = b"\xef\xbb\xbf"
DEFAULT_EXTENSIONS = (
    ".py",
    ".pyi",
    ".json",
    ".yml",
    ".yaml",
    ".toml",
    ".md",
    ".txt",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".html",
    ".css",
    ".scss",
    ".sql",
    ".ini",
    ".cfg",
)
DEFAULT_EXCLUDES = {".git", ".hg", ".svn", ".mypy_cache", "__pycache__", "node_modules", ".venv", "venv", ".pytest_cache"}
CONTROL_CHAR_CODES: Set[int] = set(range(0, 32)) - {9, 10, 13}


@dataclass
class Issue:
    path: Path
    has_bom: bool
    control_positions: List[Tuple[int, int]]  # (line_number, column_number), 1-based

    @property
    def has_control_chars(self) -> bool:
        return bool(self.control_positions)


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="扫描并清理 UTF-8 BOM 与不可见控制字符。")
    parser.add_argument("--root", default=".", help="扫描根目录（默认：当前目录）。")
    parser.add_argument(
        "--extensions",
        help="限定文件扩展名（逗号分隔，含点），例如：.py,.ts。缺省时使用通用文本扩展名。",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="扫描全部文件（会忽略 --extensions）。",
    )
    parser.add_argument(
        "--exclude",
        help="额外排除目录（逗号分隔），相对于根目录。",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="启用修复模式，移除 BOM 与控制字符后覆写原文件。",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="仅输出最终统计信息。",
    )
    parser.add_argument(
        "--show-control",
        action="store_true",
        help="显示控制字符的行列位置（默认仅在发现时输出一次提示）。",
    )
    return parser.parse_args(argv)


def resolve_extensions(args: argparse.Namespace) -> Set[str] | None:
    if args.all:
        return None
    if args.extensions:
        exts = {ext.strip().lower() for ext in args.extensions.split(",") if ext.strip()}
        return set(ext if ext.startswith(".") else f".{ext}" for ext in exts)
    return set(DEFAULT_EXTENSIONS)


def should_skip(path: Path, excludes: Set[str]) -> bool:
    parts = set(path.parts)
    return bool(parts & excludes)


def iter_files(root: Path, exts: Set[str] | None, excludes: Set[str]) -> Iterable[Path]:
    for path in root.rglob("*"):
        if path.is_dir():
            # rglob already descends into sub-directories; rely on should_skip to filter files
            continue
        if should_skip(path.relative_to(root), excludes):
            continue
        if exts is not None and path.suffix.lower() not in exts:
            continue
        yield path


def detect_control_positions(text: str) -> List[Tuple[int, int]]:
    positions: List[Tuple[int, int]] = []
    line = 1
    column = 1
    for ch in text:
        code = ord(ch)
        if code == 10:  # LF
            line += 1
            column = 1
            continue
        if code == 13:  # CR
            column = 1
            continue
        if code == 9:  # TAB
            column += 1
            continue
        if code in CONTROL_CHAR_CODES:
            positions.append((line, column))
        column += 1
    return positions


def read_text(path: Path) -> Tuple[bytes, str]:
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise UnicodeError(f"无法以 UTF-8 解析文件：{path} ({exc})")
    return raw, text


def analyze_file(path: Path) -> Issue | None:
    raw, text = read_text(path)
    has_bom = raw.startswith(BOM_BYTES)
    control_positions = detect_control_positions(text)
    if not has_bom and not control_positions:
        return None
    return Issue(path=path, has_bom=has_bom, control_positions=control_positions)


def clean_content(raw: bytes, text: str) -> bytes:
    if raw.startswith(BOM_BYTES):
        raw = raw[len(BOM_BYTES) :]
        text = text.lstrip("\ufeff")
    if not CONTROL_CHAR_CODES.intersection({ord(ch) for ch in text}):
        return raw
    cleaned_chars: List[str] = []
    for ch in text:
        if ord(ch) in CONTROL_CHAR_CODES:
            continue
        cleaned_chars.append(ch)
    return "".join(cleaned_chars).encode("utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    
    # 如果提供了文件参数，直接检查这些文件
    if argv and len(argv) > 0 and not argv[0].startswith('-'):
        # 处理文件参数模式
        files_to_check = [Path(f) for f in argv if not f.startswith('-')]
        issues: List[Issue] = []
        
        for file_path in files_to_check:
            if file_path.exists() and file_path.is_file():
                try:
                    issue = analyze_file(file_path)
                    if issue:
                        issues.append(issue)
                        if not args.quiet:
                            details: List[str] = []
                            if issue.has_bom:
                                details.append("含BOM")
                            if issue.has_control_chars:
                                if args.show_control:
                                    positions = ", ".join(f"{ln}:{col}" for ln, col in issue.control_positions[:5])
                                    suffix = "..." if len(issue.control_positions) > 5 else ""
                                    details.append(f"控制字符(位置 {positions}{suffix})")
                                else:
                                    details.append(f"控制字符({len(issue.control_positions)} 处)")
                            print(f"  - {issue.path}: {', '.join(details)}")
                except UnicodeError as err:
                    if not args.quiet:
                        print(f"[跳过] {err}", file=sys.stderr)
                    continue
        
        if issues:
            if not args.quiet:
                print(f"发现异常文件：{len(issues)}")
            if not args.fix:
                return 1
        
        if not args.quiet:
            print("未发现 BOM 或控制字符问题。")
        return 0
    
    root = Path(args.root).resolve()
    if not root.exists():
        print(f"[错误] 根目录不存在：{root}", file=sys.stderr)
        return 2

    extensions = resolve_extensions(args)
    excludes = set(DEFAULT_EXCLUDES)
    if args.exclude:
        excludes.update({item.strip() for item in args.exclude.split(",") if item.strip()})

    issues: List[Issue] = []
    total_files = 0

    for file_path in iter_files(root, extensions, excludes):
        total_files += 1
        try:
            issue = analyze_file(file_path)
        except UnicodeError as err:
            if not args.quiet:
                print(f"[跳过] {err}", file=sys.stderr)
            continue
        if issue:
            issues.append(issue)

    if not args.quiet:
        print(f"扫描目录：{root}")
        if extensions is None:
            print("匹配扩展名：全部文件")
        else:
            print(f"匹配扩展名：{', '.join(sorted(extensions))}")
        print(f"排除目录：{', '.join(sorted(excludes))}")
        print(f"总计文件：{total_files}")

    if not issues:
        if not args.quiet:
            print("未发现 BOM 或控制字符问题。")
        return 0

    if not args.quiet:
        print(f"发现异常文件：{len(issues)}")
        for issue in issues:
            details: List[str] = []
            if issue.has_bom:
                details.append("含BOM")
            if issue.has_control_chars:
                if args.show_control:
                    positions = ", ".join(f"{ln}:{col}" for ln, col in issue.control_positions[:5])
                    suffix = "..." if len(issue.control_positions) > 5 else ""
                    details.append(f"控制字符(位置 {positions}{suffix})")
                else:
                    details.append(f"控制字符({len(issue.control_positions)} 处)")
            print(f"  - {issue.path}: {', '.join(details)}")

    if not args.fix:
        return 1

    fixed_count = 0
    for issue in issues:
        raw, text = read_text(issue.path)
        cleaned = clean_content(raw, text)
        if cleaned == raw:
            continue
        issue.path.write_bytes(cleaned)
        fixed_count += 1

    if not args.quiet:
        print(f"已修复文件：{fixed_count}")

    # 再次验证
    follow_up_issues: List[Issue] = []
    for issue in issues:
        refreshed = analyze_file(issue.path)
        if refreshed:
            follow_up_issues.append(refreshed)

    if follow_up_issues:
        print("[警告] 以下文件仍存在异常，请手动核查：", file=sys.stderr)
        for issue in follow_up_issues:
            print(f"  - {issue.path}", file=sys.stderr)
        return 1

    if not args.quiet:
        print("清理完成，未发现残留问题。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
