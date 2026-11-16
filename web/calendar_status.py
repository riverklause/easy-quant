"""交易日历状态组件：首页与监控页共用。"""

import logging
from datetime import datetime
from typing import Any, Mapping, Optional, Sequence, Tuple

import dash_bootstrap_components as dbc
from dash import html

from utils.trading_calendar import CalendarError, CalendarFutureUnavailable

logger = logging.getLogger(__name__)

# 日历状态卡片覆盖的市场（展示名）
CALENDAR_MARKETS: Tuple[Tuple[str, str], ...] = (
    ("HK", "港股"),
    ("US", "美股"),
    ("CN", "A股"),
)

_SESSION_LABELS = {
    "WHOLE": "全天",
    "MORNING": "上午市",
    "AFTERNOON": "下午市",
}


def _status_alert(label: str, message: str, color: str) -> dbc.Alert:
    return dbc.Alert(f"{label}：{message}", color=color, className="py-2 mb-1")


def build_calendar_status(
    calendar: Any,
    now: Optional[datetime] = None,
    markets: Sequence[Tuple[str, str]] = CALENDAR_MARKETS,
) -> html.Div:
    """构造交易日历状态卡片内容。

    calendar 可以是 ``DataManager.get_trading_calendar()`` 的返回值，也可以是
    同契约的测试替身。四类日历异常都转成可见提示：页面不崩溃，也不静默降级。
    """
    if calendar is None:
        return html.Div(
            [_status_alert("交易日历", "尚未初始化（数据管理器不可用）", "warning")]
        )

    moment = now or datetime.now().astimezone()
    items = []
    for market, label in markets:
        try:
            session_type = calendar.get_session_type(moment, market)
        except CalendarFutureUnavailable as exc:
            items.append(_status_alert(label, f"跨年日历未发布：{exc}", "warning"))
            continue
        except CalendarError as exc:
            items.append(_status_alert(label, f"交易日历不可用：{exc}", "danger"))
            continue
        except Exception:  # noqa: BLE001 - 状态卡片不允许把页面打崩
            logger.exception("[%s] 交易日历状态检查失败", market)
            items.append(_status_alert(label, "交易日历不可用：未知错误", "danger"))
            continue

        if session_type is None:
            items.append(_status_alert(label, "今日休市", "secondary"))
            continue

        try:
            intraday = calendar.is_trading_time(moment, market)
        except CalendarError as exc:
            items.append(_status_alert(label, f"交易日历不可用：{exc}", "danger"))
            continue
        except Exception:  # noqa: BLE001
            logger.exception("[%s] 交易时段检查失败", market)
            items.append(_status_alert(label, "交易日历不可用：未知错误", "danger"))
            continue

        session_label = _SESSION_LABELS.get(str(session_type), str(session_type))
        items.append(
            _status_alert(
                label,
                f"交易日（{session_label}）· {'盘中' if intraday else '非盘中'}",
                "success" if intraday else "info",
            )
        )
    return html.Div(items)


def _format_job(entry: Optional[Mapping[str, Any]]) -> str:
    if not entry:
        return "尚未执行"
    if entry.get("ok"):
        note = entry.get("note")
        if note:
            return f"成功（{note}）"
        source = entry.get("source")
        return f"成功（{source}）" if source else "成功"
    return f"失败：{entry.get('error') or '未知错误'}"


def build_runtime_status(snapshot: Optional[Mapping[str, Any]]) -> html.Div:
    """渲染预热/盘前刷新/实时循环状态；无数据时明确显示未运行。"""
    snapshot = snapshot or {}
    warm = snapshot.get("warm") or {}
    refresh = snapshot.get("refresh") or {}
    realtime = snapshot.get("realtime") or {}

    items = []
    for market, label in CALENDAR_MARKETS:
        items.append(
            html.P(
                f"{label}：预热 {_format_job(warm.get(market))}；"
                f"盘前刷新 {_format_job(refresh.get(market))}",
                className="mb-1",
            )
        )

    if not realtime or realtime.get("updated_at") is None:
        items.append(_status_alert("实时任务", "未运行", "secondary"))
    else:
        running = bool(realtime.get("running"))
        text = (
            f"{'运行中' if running else '已停止'}；"
            f"累计跳过休市标的 {realtime.get('skipped_off_session', 0)}；"
            f"本轮跳过 {realtime.get('last_tick_skipped', 0)}"
        )
        reason = realtime.get("stopped_reason")
        if reason:
            text += f"；停止原因：{reason}"
        items.append(
            _status_alert("实时任务", text, "success" if running else "secondary")
        )

    checked_at = snapshot.get("checked_at")
    if checked_at:
        items.append(html.Small(f"状态更新时间：{checked_at}", className="text-muted"))
    return html.Div(items)
