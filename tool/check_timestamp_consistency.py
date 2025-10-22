"""
Quick audit script to detect Pydantic BaseModel classes that declare
timestamp fields but do not yet use the shared normalization helpers.

Usage:
    python tool/check_timestamp_consistency.py
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

MODEL_ROOT = Path("backend/open_webui/models")
TIMESTAMP_FIELD_PATTERN = re.compile(r"\bcreated_at\s*:\s*int\s*=\s*Field")
CLASS_HEADER_PATTERN = re.compile(r"^class\s+(\w+)\(BaseModel\):", re.MULTILINE)


@dataclass
class ModelIssue:
    file: Path
    class_name: str
    has_created_at: bool
    has_normalizer: bool


def iter_model_files() -> Iterable[Path]:
    yield from MODEL_ROOT.glob("*.py")


def analyze_file(path: Path) -> List[ModelIssue]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    issues: List[ModelIssue] = []
    matches = list(CLASS_HEADER_PATTERN.finditer(text))
    for idx, match in enumerate(matches):
        class_name = match.group(1)
        if class_name.endswith(
            (
                "Response",
                "Responses",
                "PaginationData",
                "Paginated",
                "Usage",
                "Params",
                "SimpleModel",
                "SimpleDetail",
            )
        ):
            continue
        start = match.start()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        class_block = text[start:end]
        has_created_at = TIMESTAMP_FIELD_PATTERN.search(class_block) is not None
        if not has_created_at:
            continue
        has_normalizer = any(
            substring in class_block
            for substring in (
                "normalize_required_timestamp",
                "normalize_optional_timestamp",
                "model_validate(",
                "_to_epoch",
            )
        )
        issues.append(
            ModelIssue(
                file=path,
                class_name=class_name,
                has_created_at=has_created_at,
                has_normalizer=has_normalizer,
            )
        )
    return issues


def main() -> None:
    flagged: List[ModelIssue] = []
    for file_path in iter_model_files():
        for issue in analyze_file(file_path):
            if issue.has_created_at and not issue.has_normalizer:
                flagged.append(issue)

    if not flagged:
        print("All inspected models either normalise timestamps or provide custom overrides.")
        return

    print("Models missing timestamp normalization helpers:")
    for issue in flagged:
        rel = issue.file.as_posix()
        print(f"- {rel}:{issue.class_name}")


if __name__ == "__main__":
    main()
