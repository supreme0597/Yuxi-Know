"""schedule_service 共享输入校验（时区 + cron）单元测试。

校验被 schedule_router 与 schedules skill 工具共用，本测试锁定
时区与 cron 有效性校验行为，不依赖实时数据库。
agent 存在/启用的数据有效性校验在 router/tools 中内联完成，
归属/可见性权限复用 AgentRepository.get_visible_by_slug。
"""

from __future__ import annotations

import os

# 必须在 import yuxi.* 之前设置，避免 yuxi/__init__.py 中的 config 加载抛错。
os.environ.setdefault("YUXI_SKIP_APP_INIT", "1")
os.environ.setdefault("OPENAI_API_KEY", "test-dummy-key")

import pytest

from yuxi.services.schedule_service import (
    CronError,
    TimezoneError,
    validate_cron,
    validate_timezone,
)


def test_validate_timezone_accepts_iana():
    # 合法 IANA 时区不应抛异常
    validate_timezone("Asia/Shanghai")
    validate_timezone("UTC")
    validate_timezone("America/New_York")


def test_validate_timezone_rejects_invalid():
    with pytest.raises(TimezoneError) as exc:
        validate_timezone("Not/A_Timezone")
    assert exc.value.status_code == 400
    assert "无效的时区" in exc.value.detail


def test_validate_cron_accepts_valid():
    # 合法 cron 不应抛异常（5 段标准格式）
    validate_cron("*/1 * * * *")
    validate_cron("0 9 * * 1-5")


def test_validate_cron_rejects_invalid():
    # 非法 cron（报告中的 not-a-cron 与 4 段式 * * * *）都应被拒绝
    for bad in ("not-a-cron", "* * * *"):
        with pytest.raises(CronError) as exc:
            validate_cron(bad)
        assert exc.value.status_code == 400
        assert "无效的 Cron 表达式" in exc.value.detail
