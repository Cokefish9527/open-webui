#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
hsai_video_learning_status 多租户行为校验
"""

import os
import sys
from contextlib import contextmanager

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BACKEND_ROOT = os.path.join(REPO_ROOT, "backend")
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from open_webui.models import hsai_video_learning_status as status_module
from open_webui.models.hsai_video_learning_status import (
    Base,
    HSAIVideoLearningStatuses,
    HSAIVideoLearningStatus,
    HSAIVideoLearningStatusEnum,
)

ENGINE = create_engine("sqlite:///:memory:", echo=False)
SessionLocal = sessionmaker(bind=ENGINE, autocommit=False, autoflush=False, expire_on_commit=False)


@contextmanager
def override_get_db():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    finally:
        session.close()


# 覆盖模块级 get_db，确保 ORM 使用内存数据库
status_module.get_db = override_get_db  # type: ignore


def setup_module(_):
    Base.metadata.create_all(bind=ENGINE)


def teardown_function(_):
    with ENGINE.begin() as conn:
        conn.execute(text("DELETE FROM hsai_video_learning_status"))


def test_insert_two_business_same_video():
    first = HSAIVideoLearningStatuses.insert_new_status(
        {"business_name": "COMPANY_A", "video_id": "1001", "status": "learning"}
    )
    assert first is not None

    second = HSAIVideoLearningStatuses.insert_new_status(
        {"business_name": "COMPANY_B", "video_id": "1001", "status": "learning"}
    )
    assert second is not None

    statuses = HSAIVideoLearningStatuses.get_status_map_for_business("COMPANY_A", ["1001"])
    assert statuses["1001"].status == "learning"

    statuses_other = HSAIVideoLearningStatuses.get_status_map_for_business("COMPANY_B", ["1001"])
    assert statuses_other["1001"].status == "learning"


def test_unique_constraint_same_business_video():
    HSAIVideoLearningStatuses.insert_new_status(
        {"business_name": "COMPANY_A", "video_id": "2002", "status": "learning"}
    )
    with pytest.raises(IntegrityError):
        HSAIVideoLearningStatuses.insert_new_status(
            {"business_name": "COMPANY_A", "video_id": "2002", "status": "learning"}
        )


def test_list_video_ids_by_business_filters_status():
    HSAIVideoLearningStatuses.insert_new_status(
        {"business_name": "COMPANY_A", "video_id": "3001", "status": "learning"}
    )
    HSAIVideoLearningStatuses.insert_new_status(
        {"business_name": "COMPANY_A", "video_id": "3002", "status": "learned"}
    )
    HSAIVideoLearningStatuses.insert_new_status(
        {"business_name": "COMPANY_A", "video_id": "3003", "status": "abandoned"}
    )

    learning_ids = HSAIVideoLearningStatuses.list_video_ids_by_business("COMPANY_A", status_filter="learning")
    assert set(learning_ids) == {"3001"}

    all_ids_non_pending = HSAIVideoLearningStatuses.list_video_ids_by_business("COMPANY_A")
    assert set(all_ids_non_pending) == {"3001", "3002", "3003"}

    # pending entries should be excluded unless include_pending=True
    HSAIVideoLearningStatuses.mark_pending("COMPANY_A", "3999")
    all_ids_default = HSAIVideoLearningStatuses.list_video_ids_by_business("COMPANY_A")
    assert "3999" not in set(all_ids_default)

    all_ids_with_pending = HSAIVideoLearningStatuses.list_video_ids_by_business("COMPANY_A", include_pending=True)
    assert "3999" in set(all_ids_with_pending)


def test_mark_pending_inserts_when_missing():
    pending = HSAIVideoLearningStatuses.mark_pending("COMPANY_C", "4001")
    assert pending is not None
    assert pending.status == HSAIVideoLearningStatusEnum.PENDING.value


def test_mark_pending_updates_existing_status():
    created = HSAIVideoLearningStatuses.insert_new_status(
        {"business_name": "COMPANY_D", "video_id": "5001", "status": HSAIVideoLearningStatusEnum.LEARNING.value}
    )
    assert created is not None

    updated = HSAIVideoLearningStatuses.mark_pending("COMPANY_D", "5001")
    assert updated is not None
    assert updated.status == HSAIVideoLearningStatusEnum.PENDING.value
