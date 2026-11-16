"""交易日历运行时：Web 启动预热、盘前刷新与状态快照。

只在 Web 进程内使用：
- 启动预热按市场拉当前自然年日历（cache-first，不走 prewarm 强制回源）；
- 盘前 [09:00, 09:30) 窗口内对当日开市市场 refresh 一次；
- 预热/刷新结果与实时循环统计通过线程安全快照供 /monitor 读取。

所有失败只记录 WARNING 并写入状态，不抛出到 Web 启动路径。
"""

from __future__ import annotations

import copy
import logging
import os
import threading
from datetime import date, datetime, time as dtime
from typing import Any, Callable, Dict, Mapping, Optional, Sequence, Set, Tuple

from utils.trading_calendar import CalendarError, CalendarUnavailable, market_timezone

logger = logging.getLogger(__name__)

DEFAULT_MARKETS: Tuple[str, ...] = ("HK", "US", "CN")
PRE_OPEN_START = dtime(9, 0)
PRE_OPEN_END = dtime(9, 30)  # 左闭右开：[09:00, 09:30)


def should_start_runtime(debug: bool, env: Optional[Mapping[str, str]] = None) -> bool:
    """判断当前进程是否应启动日历后台线程。

    Werkzeug debug reloader 会跑父、子两个进程；只在子进程
    （``WERKZEUG_RUN_MAIN=true``）启动，避免预热/刷新执行两遍。
    非 debug 模式没有 reloader，直接启动。
    """
    if not debug:
        return True
    source = os.environ if env is None else env
    return source.get("WERKZEUG_RUN_MAIN") == "true"


class CalendarRuntime:
    """进程内日历后台任务与状态容器（线程安全）。"""

    def __init__(
        self,
        markets: Sequence[str] = DEFAULT_MARKETS,
        now_provider: Optional[Callable[[], datetime]] = None,
        refresh_poll_interval: float = 30.0,
    ) -> None:
        self._markets = tuple(markets)
        self._now_provider = now_provider or (lambda: datetime.now().astimezone())
        self._refresh_poll_interval = refresh_poll_interval
        self._lock = threading.RLock()
        self._calendar_lock = threading.Lock()
        self._calendar_loaded = False
        self._calendar: Any = None
        self._calendar_error: Optional[Exception] = None
        self._warm: Dict[str, Dict[str, Any]] = {}
        self._refresh: Dict[str, Dict[str, Any]] = {}
        self._refresh_attempted: Set[Tuple[str, date]] = set()
        self._realtime: Dict[str, Any] = {
            "running": False,
            "skipped_off_session": 0,
            "last_tick_skipped": 0,
            "stopped_reason": None,
            "updated_at": None,
        }
        self._started = False
        self._threads: list[threading.Thread] = []
        self._stop_event = threading.Event()

    # ------------------------------------------------------------------ #
    # 生命周期
    # ------------------------------------------------------------------ #
    def start(self, data_manager: Any) -> None:
        """启动预热与盘前刷新守护线程；重复调用只生效一次。"""
        with self._lock:
            if self._started:
                return
            self._started = True

        warm_thread = threading.Thread(
            target=self._warm_thread,
            args=(data_manager,),
            name="calendar-warm",
            daemon=True,
        )
        refresh_thread = threading.Thread(
            target=self._refresh_thread,
            args=(data_manager,),
            name="calendar-preopen-refresh",
            daemon=True,
        )
        warm_thread.start()
        refresh_thread.start()
        self._threads = [warm_thread, refresh_thread]
        logger.info("交易日历后台任务已启动: %s", ", ".join(self._markets))

    def _warm_thread(self, data_manager: Any) -> None:
        try:
            self.warm_once(data_manager)
        except Exception:  # noqa: BLE001 - 后台线程不允许静默死掉
            logger.exception("交易日历启动预热线程异常")

    def _refresh_thread(self, data_manager: Any) -> None:
        while not self._stop_event.is_set():
            try:
                self.maybe_refresh(data_manager)
            except Exception:  # noqa: BLE001
                logger.exception("交易日历盘前刷新线程异常")
            if self._stop_event.wait(self._refresh_poll_interval):
                break

    def stop(self) -> None:
        self._stop_event.set()

    # ------------------------------------------------------------------ #
    # 预热 / 刷新
    # ------------------------------------------------------------------ #
    def warm_once(
        self, data_manager: Any, now: Optional[datetime] = None
    ) -> Dict[str, Dict[str, Any]]:
        """预热当前自然年 [01-01, 12-31]；单市场失败只记录。"""
        moment = self._resolve_now(now)
        calendar, setup_error = self._ensure_calendar(data_manager)
        results: Dict[str, Dict[str, Any]] = {}

        for market in self._markets:
            local = moment.astimezone(market_timezone(market))
            today = local.date()
            start = date(today.year, 1, 1)
            end = date(today.year, 12, 31)
            entry: Dict[str, Any] = {
                "ok": False,
                "source": None,
                "error": None,
                "at": self._timestamp(moment),
            }
            if setup_error is not None:
                entry["error"] = str(setup_error)
                logger.warning("[%s] 交易日历启动预热失败: %s", market, setup_error)
            else:
                try:
                    calendar.get_trading_days(market, start, end)
                    entry["ok"] = True
                    entry["source"] = getattr(calendar, "last_source", None)
                except CalendarError as exc:
                    entry["error"] = str(exc)
                    logger.warning("[%s] 交易日历启动预热失败: %s", market, exc)
                except Exception as exc:  # noqa: BLE001
                    entry["error"] = repr(exc)
                    logger.exception("[%s] 交易日历启动预热异常", market)

            results[market] = entry
            with self._lock:
                self._warm[market] = entry
        return copy.deepcopy(results)

    def maybe_refresh(
        self, data_manager: Any, now: Optional[datetime] = None
    ) -> Dict[str, Dict[str, Any]]:
        """开盘前 30 分钟窗口内刷新当天日历，每市场每天最多一次。"""
        moment = self._resolve_now(now)
        calendar, setup_error = self._ensure_calendar(data_manager)
        results: Dict[str, Dict[str, Any]] = {}

        for market in self._markets:
            local = moment.astimezone(market_timezone(market))
            if local.weekday() >= 5:
                continue
            if not (PRE_OPEN_START <= local.time() < PRE_OPEN_END):
                continue

            today = local.date()
            key = (market, today)
            with self._lock:
                if key in self._refresh_attempted:
                    continue
                # 先记“今日已尝试”：失败当天也不再重试，避免风暴。
                self._refresh_attempted.add(key)

            entry: Dict[str, Any] = {
                "ok": False,
                "error": None,
                "note": None,
                "at": self._timestamp(moment),
            }
            if setup_error is not None:
                entry["error"] = str(setup_error)
                logger.warning("[%s] 盘前刷新失败: %s", market, setup_error)
            else:
                try:
                    if calendar.is_trading_day(today, market):
                        calendar.refresh(market, today, today)
                        entry["ok"] = True
                    else:
                        entry["ok"] = True
                        entry["note"] = "休市"
                except CalendarError as exc:
                    entry["error"] = str(exc)
                    logger.warning("[%s] 盘前刷新失败: %s", market, exc)
                except Exception as exc:  # noqa: BLE001
                    entry["error"] = repr(exc)
                    logger.exception("[%s] 盘前刷新异常", market)

            results[market] = entry
            with self._lock:
                self._refresh[market] = entry
        return copy.deepcopy(results)

    # ------------------------------------------------------------------ #
    # 实时状态
    # ------------------------------------------------------------------ #
    def record_realtime(self, stats: Mapping[str, Any]) -> None:
        """接收 StrategyExecutor 的实时快照，供监控页读取。"""
        payload = {
            "running": bool(stats.get("running", False)),
            "skipped_off_session": int(stats.get("skipped_off_session", 0) or 0),
            "last_tick_skipped": int(stats.get("last_tick_skipped", 0) or 0),
            "stopped_reason": stats.get("stopped_reason"),
            "updated_at": stats.get("updated_at") or self._timestamp(self._resolve_now(None)),
        }
        with self._lock:
            self._realtime = payload

    def snapshot(self) -> Dict[str, Any]:
        """返回监控页可读的状态快照。"""
        with self._lock:
            return {
                "warm": copy.deepcopy(self._warm),
                "refresh": copy.deepcopy(self._refresh),
                "realtime": dict(self._realtime),
                "checked_at": self._timestamp(self._resolve_now(None)),
            }

    # ------------------------------------------------------------------ #
    # 内部工具
    # ------------------------------------------------------------------ #
    def _ensure_calendar(self, data_manager: Any) -> Tuple[Any, Optional[Exception]]:
        """预热/刷新线程共用同一份日历解析结果，避免并发创建两个实例。"""
        with self._calendar_lock:
            if not self._calendar_loaded:
                self._calendar, self._calendar_error = self._resolve_calendar(data_manager)
                self._calendar_loaded = True
            return self._calendar, self._calendar_error

    def _resolve_calendar(self, data_manager: Any) -> Tuple[Any, Optional[Exception]]:
        getter = getattr(data_manager, "get_trading_calendar", None)
        if getter is None:
            return None, CalendarUnavailable("data_manager 未提供 get_trading_calendar")
        try:
            return getter(), None
        except Exception as exc:  # noqa: BLE001 - 创建失败按日历不可用记录
            return None, exc

    def _resolve_now(self, now: Optional[datetime]) -> datetime:
        moment = now or self._now_provider()
        if not isinstance(moment, datetime) or moment.tzinfo is None:
            raise ValueError("日历运行时的时间必须 tz-aware")
        return moment

    @staticmethod
    def _timestamp(moment: datetime) -> str:
        return moment.isoformat(timespec="seconds")


_runtime: Optional[CalendarRuntime] = None
_runtime_lock = threading.Lock()


def get_runtime() -> CalendarRuntime:
    """返回进程内单例，供 app 启动与监控页共用。"""
    global _runtime
    with _runtime_lock:
        if _runtime is None:
            _runtime = CalendarRuntime()
        return _runtime
