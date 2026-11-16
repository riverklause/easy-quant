"""交易日历能力层（Trading Calendar）。

唯一权威来源是 futu `request_trading_days`；本地按市场落一份 parquet + coverage
meta 缓存。缓存不完整、窗口越界、未来未发布等情形一律显式报错，不做工作日降级。

设计文档：docs/trading_calendar.md
"""

from __future__ import annotations

import csv
import hashlib
import json
import logging
import os
import re
import threading
import time as _time
from collections import deque
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime, time as dtime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Iterator, List, Optional, Sequence, Tuple
from zoneinfo import ZoneInfo

import pandas as pd

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CACHE_DIR = _PROJECT_ROOT / "data" / "cache" / "trading_calendar"
DEFAULT_OVERRIDES_DIR = _PROJECT_ROOT / "data" / "calendars"

MARKET_TIMEZONES: Dict[str, str] = {
    "HK": "Asia/Hong_Kong",
    "US": "America/New_York",
    "CN": "Asia/Shanghai",
}

_MARKET_ALIASES: Dict[str, str] = {
    "HK": "HK",
    "HKG": "HK",
    "US": "US",
    "USA": "US",
    "CN": "CN",
    "SH": "CN",
    "SSE": "CN",
    "SZ": "CN",
    "SZSE": "CN",
}

# 市场默认时段（不含竞价段）；close_time override 只截断最后一个 segment。
_SESSION_TEMPLATES: Dict[str, List[Tuple[dtime, dtime]]] = {
    "HK": [(dtime(9, 30), dtime(12, 0)), (dtime(13, 0), dtime(16, 0))],
    "US": [(dtime(9, 30), dtime(16, 0))],
    "CN": [(dtime(9, 30), dtime(11, 30)), (dtime(13, 0), dtime(15, 0))],
}

VALID_SESSION_TYPES = ("WHOLE", "MORNING", "AFTERNOON")
_SESSION_TYPE_ALIASES = {
    "WHOLE": "WHOLE",
    "FULL": "WHOLE",
    "AM": "MORNING",
    "MORNING": "MORNING",
    "PM": "AFTERNOON",
    "AFTERNOON": "AFTERNOON",
}

_CLOSE_TIME_RE = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")


# --------------------------------------------------------------------------- #
# 异常
# --------------------------------------------------------------------------- #
class CalendarError(Exception):
    """交易日历异常基类。"""


class CalendarUnavailable(CalendarError):
    """futu 不可用且缓存无法完整覆盖（含窗口内覆盖空洞）。"""


class CalendarOutOfRange(CalendarError):
    """工作日早于 10 年窗口且无缓存。"""


class CalendarFutureUnavailable(CalendarError):
    """未来侧未覆盖、负缓存命中、或整段请求超出今年 12/31。"""


class CalendarRateLimited(CalendarError):
    """退避重试后仍被限流。"""


# --------------------------------------------------------------------------- #
# 市场 / 日期工具
# --------------------------------------------------------------------------- #
def normalize_market(market: str) -> str:
    """正规化市场代码：SH/SZ → CN，支持 HK.00700 这类前缀。"""
    if not isinstance(market, str) or not market.strip():
        raise ValueError(f"非法市场代码: {market!r}")
    key = market.strip().upper()
    if "." in key:
        key = key.split(".", 1)[0]
    if key not in _MARKET_ALIASES:
        raise ValueError(f"不支持的市场: {market!r}")
    return _MARKET_ALIASES[key]


def market_timezone(market: str) -> ZoneInfo:
    return ZoneInfo(MARKET_TIMEZONES[normalize_market(market)])


# futu 前缀 / yfinance 后缀 → 市场；BJ 明确返回 None（本期不支持北交所）
_SYMBOL_PREFIX_MARKETS: Dict[str, Optional[str]] = {
    "HK": "HK",
    "US": "US",
    "SH": "CN",
    "SZ": "CN",
    "CN": "CN",
    "BJ": None,
}
_SYMBOL_SUFFIX_MARKETS: Dict[str, Optional[str]] = {
    "HK": "HK",
    "US": "US",
    "SS": "CN",
    "SH": "CN",
    "SZ": "CN",
    "CN": "CN",
    "BJ": None,
}


def _infer_one_market(symbol: Any) -> Optional[str]:
    if not isinstance(symbol, str):
        return None
    text = symbol.strip().upper()
    if not text:
        return None
    if "." in text:
        head, tail = text.split(".", 1)
        if head in _SYMBOL_PREFIX_MARKETS:
            return _SYMBOL_PREFIX_MARKETS[head]
        if tail in _SYMBOL_SUFFIX_MARKETS:
            return _SYMBOL_SUFFIX_MARKETS[tail]
        return None
    # 裸代码只认纯字母美股；数字裸代码无法区分沪/深，按未知处理。
    # 裸市场码（HK/US/CN/SH/SZ/BJ）不是标的，返回 None，避免误判为美股。
    if text in _SYMBOL_PREFIX_MARKETS:
        return None
    return "US" if text.isalpha() else None


def infer_market(symbol: Any) -> Optional[str]:
    """从股票代码推断市场；无法唯一确定（含北交所、跨市场）返回 None。

    支持 futu 前缀（HK.00700 / US.AAPL / SH.600000 / SZ.000001）、
    yfinance 后缀（0700.HK / 600000.SS / 000001.SZ）与裸美股代码（AAPL）。
    传入可迭代对象时，仅当所有代码同属一个市场才返回该市场。
    """
    if symbol is None:
        return None
    if isinstance(symbol, str):
        return _infer_one_market(symbol)
    try:
        symbols = list(symbol)
    except TypeError:
        return None
    if not symbols:
        return None

    markets = {_infer_one_market(item) for item in symbols}
    if len(markets) == 1:
        return markets.pop()
    return None


def _minus_years(day: date, years: int) -> date:
    try:
        return day.replace(year=day.year - years)
    except ValueError:  # 2/29
        return day.replace(year=day.year - years, day=28)


def _is_weekend(day: date) -> bool:
    return day.weekday() >= 5


def _date_range(start: date, end: date) -> Iterator[date]:
    cur = start
    while cur <= end:
        yield cur
        cur += timedelta(days=1)


def _empty_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.Series(dtype="datetime64[ns]"),
            "session_type": pd.Series(dtype="object"),
        }
    )


def _coerce_day(value: Any, market: str) -> date:
    """把日期型入参转成市场本地日期。

    - date / YYYY-MM-DD / naive 零点 Timestamp → 直接作为市场本地日期；
    - tz-aware 时间 → 按时刻换算到市场时区；
    - 带时分秒的 naive datetime → ValueError。
    """
    if isinstance(value, datetime):
        if value.tzinfo is None:
            if value.hour or value.minute or value.second or value.microsecond:
                raise ValueError(f"naive 时间必须 tz-aware: {value!r}")
            return value.date()
        return value.astimezone(market_timezone(market)).date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return datetime.strptime(value.strip(), "%Y-%m-%d").date()
        except ValueError as exc:
            raise ValueError(f"日期格式必须 YYYY-MM-DD: {value!r}") from exc
    raise ValueError(f"无法识别的日期入参: {value!r}")


def _coerce_instant(value: Any, market: str) -> datetime:
    """is_trading_time 专用：必须是带时区的时刻。"""
    if not isinstance(value, datetime):
        raise ValueError(f"需要 tz-aware datetime: {value!r}")
    if value.tzinfo is None:
        raise ValueError(f"naive 时间必须 tz-aware: {value!r}")
    return value.astimezone(market_timezone(market))


def _segments_for(market: str, session_type: str) -> List[Tuple[dtime, dtime]]:
    segments = list(_SESSION_TEMPLATES[market])
    if session_type == "MORNING":
        return segments[:1]
    if session_type == "AFTERNOON":
        return segments[-1:]
    return segments


# --------------------------------------------------------------------------- #
# futu 返回解析
# --------------------------------------------------------------------------- #
def normalize_trading_days_payload(payload: Any, market: str = "HK") -> pd.DataFrame:
    """把 futu 的 list[dict] / 旧版 DataFrame 统一成 date + session_type。

    - 排序、去重（同日保留最后一条）；
    - 无法识别的 trade_date_type → ValueError；
    - 美股出现 MORNING/AFTERNOON → 降级为 WHOLE 并 WARNING。
    """
    mkt = normalize_market(market)

    if isinstance(payload, pd.DataFrame):
        frame = payload.copy()
    elif isinstance(payload, dict):
        raise ValueError(f"无法解析的交易日历返回: {type(payload)!r}")
    elif isinstance(payload, Iterable) and not isinstance(payload, (str, bytes)):
        rows = list(payload)
        if not rows:
            return _empty_frame()
        if isinstance(rows[0], dict):
            records = []
            for row in rows:
                records.append(
                    {
                        "date": row.get("time") or row.get("date") or row.get("trade_date"),
                        "session_type": row.get("trade_date_type")
                        or row.get("session_type")
                        or row.get("type"),
                    }
                )
            frame = pd.DataFrame(records)
        else:
            frame = pd.DataFrame(rows, columns=["date", "session_type"])
    else:
        raise ValueError(f"无法解析的交易日历返回: {type(payload)!r}")

    renamed: Dict[Any, str] = {}
    for col in frame.columns:
        key = str(col).strip().lower()
        if key in ("time", "date", "trade_date", "trade_date_str") and "date" not in renamed.values():
            renamed[col] = "date"
        elif key in ("trade_date_type", "session_type", "type") and "session_type" not in renamed.values():
            renamed[col] = "session_type"
    frame = frame.rename(columns=renamed)

    if "date" not in frame.columns:
        raise ValueError("交易日历返回缺少 date/time 列")
    if "session_type" not in frame.columns:
        frame["session_type"] = "WHOLE"

    parsed = pd.to_datetime(frame["date"], errors="coerce")
    invalid = int(parsed.isna().sum())
    if invalid:
        logger.warning("交易日历返回中有 %s 行日期无法解析，已忽略", invalid)
    frame = frame.loc[parsed.notna()].copy()
    frame["date"] = parsed[parsed.notna()].dt.normalize()

    types = frame["session_type"].map(
        lambda x: _SESSION_TYPE_ALIASES.get(str(x).strip().upper(), None)
        if pd.notna(x)
        else "WHOLE"
    )
    unknown = frame.loc[types.isna(), "session_type"].unique().tolist()
    if unknown:
        raise ValueError(f"无法识别的 trade_date_type: {unknown}")
    frame["session_type"] = types.astype(str)

    if mkt == "US":
        mask = frame["session_type"] != "WHOLE"
        if bool(mask.any()):
            logger.warning("美股返回了 MORNING/AFTERNOON，按 WHOLE 处理")
            frame.loc[mask, "session_type"] = "WHOLE"

    frame = frame.drop_duplicates(subset=["date"], keep="last")
    frame = frame.sort_values("date").reset_index(drop=True)
    return frame[["date", "session_type"]]


# --------------------------------------------------------------------------- #
# 限流
# --------------------------------------------------------------------------- #
class RateLimiter:
    """进程内限流：最小间隔 + 固定窗口 token bucket。"""

    def __init__(
        self,
        min_interval: float = 1.1,
        max_calls: int = 25,
        window: float = 30.0,
        clock: Callable[[], float] = _time.monotonic,
        sleep: Callable[[float], None] = _time.sleep,
    ) -> None:
        self.min_interval = min_interval
        self.max_calls = max_calls
        self.window = window
        self._clock = clock
        self._sleep = sleep
        self._stamps: deque[float] = deque()
        self._last: Optional[float] = None
        self._lock = threading.Lock()

    def acquire(self) -> None:
        # 锁内预订时间槽：并发线程拿到的是不同 slot，不会同时睡醒后一起放行。
        with self._lock:
            now = self._clock()
            while self._stamps and now - self._stamps[0] >= self.window:
                self._stamps.popleft()
            slot = now
            if self._last is not None:
                slot = max(slot, self._last + self.min_interval)
            if len(self._stamps) >= self.max_calls:
                slot = max(slot, self._stamps[0] + self.window)
            self._stamps.append(slot)
            self._last = slot
        while True:
            wait = slot - self._clock()
            if wait <= 0:
                break
            self._sleep(wait)


# --------------------------------------------------------------------------- #
# 缓存
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class _Interval:
    start: date
    end: date
    fetched_at: datetime


def _sha256(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@contextmanager
def _file_lock(path: Path) -> Iterator[None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = open(path, "a+b")
    try:
        if os.name == "nt":
            import msvcrt

            handle.seek(0)
            while True:
                try:
                    msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
                    break
                except OSError:
                    _time.sleep(0.05)
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        yield
    finally:
        try:
            if os.name == "nt":
                import msvcrt

                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            handle.close()


def _add_interval(intervals: Sequence[_Interval], start: date, end: date, fetched_at: datetime) -> List[_Interval]:
    """写入区间：裁剪重叠旧段；相邻且 fetched_at 相同才合并。"""
    if start > end:
        return list(intervals)

    pieces: List[_Interval] = []
    for interval in intervals:
        if interval.end < start or interval.start > end:
            pieces.append(interval)
            continue
        if interval.start < start:
            pieces.append(_Interval(interval.start, start - timedelta(days=1), interval.fetched_at))
        if interval.end > end:
            pieces.append(_Interval(end + timedelta(days=1), interval.end, interval.fetched_at))
    pieces.append(_Interval(start, end, fetched_at))
    pieces.sort(key=lambda item: item.start)

    merged: List[_Interval] = []
    for piece in pieces:
        if (
            merged
            and piece.start <= merged[-1].end + timedelta(days=1)
            and merged[-1].fetched_at == piece.fetched_at
        ):
            previous = merged[-1]
            merged[-1] = _Interval(previous.start, max(previous.end, piece.end), previous.fetched_at)
        else:
            merged.append(piece)
    return merged


def _missing_ranges(intervals: Sequence[_Interval], start: date, end: date) -> List[Tuple[date, date]]:
    missing: List[Tuple[date, date]] = []
    cursor = start
    for interval in sorted(intervals, key=lambda item: item.start):
        if interval.end < cursor:
            continue
        if interval.start > end:
            break
        if interval.start > cursor:
            missing.append((cursor, min(interval.start - timedelta(days=1), end)))
        cursor = max(cursor, interval.end + timedelta(days=1))
        if cursor > end:
            break
    if cursor <= end:
        missing.append((cursor, end))
    return missing


def _covers(intervals: Sequence[_Interval], start: date, end: date) -> bool:
    """区间是否已覆盖：周末是结构性休市，不要求落在 covered_intervals 内。"""
    return not _missing_workdays(intervals, start, end)


def _coverage_right(intervals: Sequence[_Interval]) -> Optional[date]:
    return max((item.end for item in intervals), default=None)


def _fetched_at_for(
    intervals: Sequence[_Interval], start: date, end: date
) -> Optional[datetime]:
    """请求区间内覆盖段的最新 fetched_at，用于 last_fetched_at。"""
    stamps = [
        item.fetched_at for item in intervals if item.start <= end and item.end >= start
    ]
    return max(stamps) if stamps else None


def _merge_ranges(ranges: Sequence[Tuple[date, date]]) -> List[Tuple[date, date]]:
    """合并请求区间：排序后合并重叠/相邻段。"""
    merged: List[Tuple[date, date]] = []
    for start, end in sorted(item for item in ranges if item[0] <= item[1]):
        if merged and start <= merged[-1][1] + timedelta(days=1):
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


class _CalendarStore:
    """每市场单 parquet + coverage meta，原子写 + 文件锁。"""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)

    def _paths(self, market: str) -> Tuple[Path, Path, Path]:
        return (
            self.root / f"{market}.parquet",
            self.root / f"{market}.meta.json",
            self.root / f"{market}.lock",
        )

    def read(self, market: str) -> Tuple[pd.DataFrame, List[_Interval], Optional[datetime]]:
        parquet_path, meta_path, _ = self._paths(market)
        if not meta_path.exists():
            if parquet_path.exists():
                logger.warning("交易日历缓存缺 meta，按损坏处理: %s", parquet_path)
            return _empty_frame(), [], None

        try:
            with open(meta_path, "r", encoding="utf-8") as handle:
                meta = json.load(handle)
        except (OSError, ValueError) as exc:
            logger.warning("交易日历 meta 读取失败，按损坏处理: %s", exc)
            return _empty_frame(), [], None

        intervals = []
        for item in meta.get("covered_intervals") or []:
            try:
                intervals.append(
                    _Interval(
                        start=date.fromisoformat(item["start"]),
                        end=date.fromisoformat(item["end"]),
                        fetched_at=datetime.fromisoformat(item["fetched_at"]),
                    )
                )
            except (KeyError, TypeError, ValueError):
                logger.warning("交易日历 meta 中有非法区间，已忽略: %r", item)

        probe = None
        raw_probe = meta.get("future_probe_at")
        if raw_probe:
            try:
                probe = datetime.fromisoformat(raw_probe)
            except ValueError:
                logger.warning("交易日历 meta 中 future_probe_at 非法: %r", raw_probe)

        if not parquet_path.exists():
            logger.warning("交易日历缓存缺 parquet，按损坏处理: %s", parquet_path)
            return _empty_frame(), [], None

        expected = meta.get("parquet_sha256")
        actual = _sha256(parquet_path)
        for _ in range(2):
            if not expected or actual == expected:
                break
            # 写路径是原子替换，短暂重试通常即可对齐；不取文件锁重读，
            # 避免 write 持锁期间同进程嵌套加锁死锁。
            _time.sleep(0.05)
            actual = _sha256(parquet_path)
        if expected and actual != expected:
            logger.warning("交易日历 parquet 与 meta sha 不匹配，按损坏处理: %s", parquet_path)
            return _empty_frame(), [], None

        try:
            frame = pd.read_parquet(parquet_path)
            if "date" not in frame.columns or "session_type" not in frame.columns:
                raise ValueError("缺少 date/session_type 列")
            frame = frame[["date", "session_type"]].copy()
            frame["date"] = pd.to_datetime(frame["date"]).dt.normalize()
            frame["session_type"] = frame["session_type"].astype(str)
            frame = frame.sort_values("date").reset_index(drop=True)
        except Exception as exc:  # noqa: BLE001 - 读盘失败统一按损坏处理
            logger.warning("交易日历 parquet 读取失败，按损坏处理: %s", exc)
            return _empty_frame(), [], None

        return frame, intervals, probe

    def write(
        self,
        market: str,
        frame: pd.DataFrame,
        intervals: Sequence[_Interval],
        probe_at: Optional[datetime],
        *,
        write_rows: bool,
    ) -> Tuple[pd.DataFrame, List[_Interval], Optional[datetime]]:
        parquet_path, meta_path, lock_path = self._paths(market)
        self.root.mkdir(parents=True, exist_ok=True)

        with _file_lock(lock_path):
            # 合并磁盘上已有内容，避免并发写入丢 coverage
            disk_frame = _empty_frame()
            disk_intervals: List[_Interval] = []
            try:
                disk_frame, disk_intervals, _ = self.read(market)
            except Exception:  # noqa: BLE001
                pass
            intervals = list(intervals)
            for item in disk_intervals:
                intervals = _add_interval(intervals, item.start, item.end, item.fetched_at)
            if write_rows and not disk_frame.empty:
                frame = pd.concat([disk_frame, frame], ignore_index=True)
                frame = frame.drop_duplicates(subset=["date"], keep="last")
                frame = frame.sort_values("date").reset_index(drop=True)
            intervals = sorted(intervals, key=lambda item: item.start)

            if write_rows:
                tmp_path = parquet_path.with_suffix(".parquet.tmp")
                frame.to_parquet(tmp_path, index=False)
                os.replace(tmp_path, parquet_path)
                sha = _sha256(parquet_path)
            else:
                sha = _sha256(parquet_path)
                if sha is None:
                    existing = {}
                    if meta_path.exists():
                        try:
                            with open(meta_path, "r", encoding="utf-8") as handle:
                                existing = json.load(handle)
                        except (OSError, ValueError):
                            existing = {}
                    sha = existing.get("parquet_sha256")

            meta = {
                "schema_version": 1,
                "market": market,
                "covered_intervals": [
                    {
                        "start": item.start.isoformat(),
                        "end": item.end.isoformat(),
                        "fetched_at": item.fetched_at.isoformat(),
                    }
                    for item in intervals
                ],
                "future_probe_at": probe_at.isoformat() if probe_at else None,
                "source": "futu",
                "row_count": int(len(frame)),
                "parquet_sha256": sha,
            }
            tmp_meta = meta_path.with_suffix(".json.tmp")
            with open(tmp_meta, "w", encoding="utf-8") as handle:
                json.dump(meta, handle, ensure_ascii=False, indent=2)
            os.replace(tmp_meta, meta_path)

        return frame, list(intervals), probe_at


# --------------------------------------------------------------------------- #
# 交易日历
# --------------------------------------------------------------------------- #
class TradingCalendar:
    """交易日历能力层。

    取数顺序：本地缓存（完整覆盖且当年未过 TTL）→ futu → 旧缓存（WARNING）→ 抛错。
    """

    def __init__(
        self,
        client: Any = None,
        cache_dir: Optional[Path | str] = None,
        overrides_dir: Optional[Path | str] = None,
        refresh_ttl: float = 12 * 3600,
        future_probe_ttl: float = 12 * 3600,
        now_provider: Optional[Callable[[], datetime]] = None,
        rate_limiter: Optional[Any] = None,
        retry_backoff: Sequence[float] = (1.0, 2.0),
    ) -> None:
        self.client = client
        self.cache_dir = Path(cache_dir) if cache_dir else DEFAULT_CACHE_DIR
        self.overrides_dir = Path(overrides_dir) if overrides_dir else DEFAULT_OVERRIDES_DIR
        self.refresh_ttl = float(refresh_ttl)
        self.future_probe_ttl = float(future_probe_ttl)
        self._now_provider = now_provider or (lambda: datetime.now().astimezone())
        self.rate_limiter = rate_limiter or RateLimiter()
        self.retry_backoff = tuple(retry_backoff)

        self._store = _CalendarStore(self.cache_dir)
        self._frames: Dict[str, pd.DataFrame] = {}
        self._intervals: Dict[str, List[_Interval]] = {}
        self._probes: Dict[str, Optional[datetime]] = {}
        self._loaded: set[str] = set()
        self._market_locks: Dict[str, threading.RLock] = {
            mkt: threading.RLock() for mkt in MARKET_TIMEZONES
        }
        self._state: Dict[str, Dict[str, Any]] = {}
        self._last_market: Optional[str] = None
        self._warned_overrides: set[str] = set()

    # -- 对外属性 ---------------------------------------------------------- #
    @property
    def last_source(self) -> Optional[str]:
        if self._last_market is None:
            return None
        return self._state.get(self._last_market, {}).get("source")

    @property
    def cache_stale(self) -> bool:
        if self._last_market is None:
            return False
        return bool(self._state.get(self._last_market, {}).get("stale"))

    @property
    def last_fetched_at(self) -> Optional[datetime]:
        if self._last_market is None:
            return None
        return self._state.get(self._last_market, {}).get("fetched_at")

    # -- 公开 API ---------------------------------------------------------- #
    def session_date(self, value: Any, market: str) -> date:
        """把时刻/日期换算成市场本地 session date。"""
        mkt = normalize_market(market)
        return _coerce_day(value, mkt)

    def is_trading_day(self, day: Any, market: str, refresh: bool = False) -> bool:
        mkt = normalize_market(market)
        target = _coerce_day(day, mkt)
        if _is_weekend(target):
            self._mark(mkt, "cache", False)
            return False
        frame = self._ensure_coverage(mkt, target, target, refresh=refresh, allow_partial=False)
        return target in set(frame["date"].dt.date)

    def get_session_type(self, day: Any, market: str, refresh: bool = False) -> Optional[str]:
        mkt = normalize_market(market)
        target = _coerce_day(day, mkt)
        if _is_weekend(target):
            self._mark(mkt, "cache", False)
            return None
        frame = self._ensure_coverage(mkt, target, target, refresh=refresh, allow_partial=False)
        rows = frame.loc[frame["date"].dt.date == target, "session_type"]
        return None if rows.empty else str(rows.iloc[0])

    def get_trading_days(
        self,
        market: str,
        start: Any = None,
        end: Any = None,
        refresh: bool = False,
    ) -> pd.DatetimeIndex:
        mkt = normalize_market(market)
        today = self._today(mkt)
        end_day = _coerce_day(end, mkt) if end is not None else today
        start_day = _coerce_day(start, mkt) if start is not None else end_day - timedelta(days=365)
        if start_day > end_day:
            raise ValueError(f"start 不能晚于 end: {start_day} > {end_day}")

        if all(_is_weekend(day) for day in _date_range(start_day, end_day)):
            self._mark(mkt, "cache", False)
            return pd.DatetimeIndex([])

        frame = self._ensure_coverage(mkt, start_day, end_day, refresh=refresh, allow_partial=True)
        dates = frame["date"].dt.date
        mask = (dates >= start_day) & (dates <= end_day)
        return pd.DatetimeIndex(frame.loc[mask, "date"].sort_values().tolist())

    def get_calendar_frame(
        self,
        market: str,
        start: Any = None,
        end: Any = None,
        refresh: bool = False,
    ) -> pd.DataFrame:
        mkt = normalize_market(market)
        today = self._today(mkt)
        end_day = _coerce_day(end, mkt) if end is not None else today
        start_day = _coerce_day(start, mkt) if start is not None else end_day - timedelta(days=365)
        if start_day > end_day:
            raise ValueError(f"start 不能晚于 end: {start_day} > {end_day}")

        frame = self._ensure_coverage(mkt, start_day, end_day, refresh=refresh, allow_partial=True)
        dates = frame["date"].dt.date
        result = frame.loc[(dates >= start_day) & (dates <= end_day)].copy()
        some_day = result["date"].dt.date.values

        overrides = self._validated_overrides(mkt, frame)
        result["close_time"] = [
            overrides[day][0].strftime("%H:%M") if day in overrides else None for day in some_day
        ]
        return result.reset_index(drop=True)

    def is_trading_time(self, value: Any, market: str, refresh: bool = False) -> bool:
        mkt = normalize_market(market)
        local = _coerce_instant(value, mkt)
        target = local.date()
        if _is_weekend(target):
            return False
        frame = self._ensure_coverage(mkt, target, target, refresh=refresh, allow_partial=False)
        rows = frame.loc[frame["date"].dt.date == target, "session_type"]
        if rows.empty:
            return False

        segments = _segments_for(mkt, str(rows.iloc[0]))
        overrides = self._validated_overrides(mkt, frame)
        if target in overrides:
            close_time = overrides[target][0]
            segments[-1] = (segments[-1][0], close_time)

        current = local.time()
        return any(begin <= current < finish for begin, finish in segments)

    def next_trading_day(self, day: Any, market: str) -> pd.Timestamp:
        mkt = normalize_market(market)
        target = _coerce_day(day, mkt)
        _, max_date, _ = self._window(mkt)
        cursor = target + timedelta(days=1)
        while True:
            if cursor > max_date:
                raise CalendarFutureUnavailable(
                    f"[{mkt}] {target} 之后无可用交易日：已超出可发布窗口 {max_date}"
                )
            chunk_end = min(cursor + timedelta(days=59), max_date)
            days = self.get_trading_days(mkt, cursor, chunk_end)
            if len(days):
                return days[0]
            cursor = chunk_end + timedelta(days=1)

    def previous_trading_day(self, day: Any, market: str) -> pd.Timestamp:
        mkt = normalize_market(market)
        target = _coerce_day(day, mkt)
        min_date, _, _ = self._window(mkt)
        cursor = target - timedelta(days=1)
        while True:
            if cursor >= min_date:
                chunk_start = max(cursor - timedelta(days=59), min_date)
            else:
                chunk_start = cursor - timedelta(days=59)
            days = self.get_trading_days(mkt, chunk_start, cursor)
            if len(days):
                return days[-1]
            cursor = chunk_start - timedelta(days=1)

    def refresh(self, market: str, start: Any = None, end: Any = None) -> pd.DatetimeIndex:
        return self.get_trading_days(market, start, end, refresh=True)

    def prewarm(self, market: str, start: Any, end: Any) -> None:
        mkt = normalize_market(market)
        start_day = _coerce_day(start, mkt)
        end_day = _coerce_day(end, mkt)
        self._ensure_coverage(
            mkt, start_day, end_day, refresh=True, allow_partial=True, prewarming=True
        )

    # -- 内部：窗口 / 缓存 -------------------------------------------------- #
    def _now(self) -> datetime:
        value = self._now_provider()
        if not isinstance(value, datetime) or value.tzinfo is None:
            raise ValueError("now_provider 必须返回 tz-aware datetime")
        return value

    def _today(self, market: str) -> date:
        return self._now().astimezone(market_timezone(market)).date()

    def _window(self, market: str) -> Tuple[date, date, date]:
        today = self._today(market)
        return _minus_years(today, 10), date(today.year, 12, 31), today

    def _load(self, market: str) -> None:
        if market in self._loaded:
            return
        frame, intervals, probe = self._store.read(market)
        if probe is not None and probe.year != self._today(market).year:
            # 负缓存只在同一自然年内有效：跨年即失效并清空，
            # 避免 12/31 的探测压住 1/1 的新日历。
            logger.warning(
                "[%s] future_probe_at 跨年失效，已清空: %s", market, probe.isoformat()
            )
            probe = None
            if intervals:
                frame, intervals, probe = self._store.write(
                    market, frame, intervals, None, write_rows=False
                )
        self._frames[market] = frame
        self._intervals[market] = intervals
        self._probes[market] = probe
        self._loaded.add(market)

    def _mark(self, market: str, source: str, stale: bool, fetched_at: Optional[datetime] = None) -> None:
        self._last_market = market
        self._state[market] = {"source": source, "stale": stale, "fetched_at": fetched_at or self._now()}

    def _probe_fresh(self, probe: Optional[datetime], today: date) -> bool:
        if probe is None or probe.year != today.year:
            return False
        return (self._now() - probe).total_seconds() < self.future_probe_ttl

    def _current_year_stale(
        self, intervals: Sequence[_Interval], start: date, end: date, today: date
    ) -> bool:
        """当年窗口内任一覆盖段过期即 stale；没有相交段也视为 stale。"""
        window_start = max(start, date(today.year, 1, 1))
        window_end = min(end, date(today.year, 12, 31))
        if window_start > window_end:
            return False
        now = self._now()
        intersecting = [
            interval
            for interval in intervals
            if interval.start <= window_end and interval.end >= window_start
        ]
        if not intersecting:
            return True
        return any(
            (now - interval.fetched_at).total_seconds() > self.refresh_ttl
            for interval in intersecting
        )

    def _intersects_current_year(self, start: date, end: date, today: date) -> bool:
        return start.year == today.year or end.year == today.year or (start <= date(today.year, 1, 1) <= end)

    # -- 内部：覆盖与回源 -------------------------------------------------- #
    def _ensure_coverage(
        self,
        market: str,
        start: date,
        end: date,
        *,
        refresh: bool,
        allow_partial: bool,
        prewarming: bool = False,
    ) -> pd.DataFrame:
        if start > end:
            raise ValueError(f"start 不能晚于 end: {start} > {end}")

        with self._market_locks[market]:
            self._load(market)
            frame = self._frames[market]
            intervals = self._intervals[market]
            probe = self._probes[market]

            # 纯周末区间：结构性休市，不需要 coverage，也不该触发请求
            if all(_is_weekend(day) for day in _date_range(start, end)):
                self._mark(market, "cache", False)
                return frame

            min_date, max_date, today = self._window(market)

            # 历史侧：窗口外只能读缓存
            hist_start = start
            if end < min_date:
                # 整段早于 10 年窗口：只能读缓存，futu 不再提供
                if refresh:
                    raise CalendarOutOfRange(
                        f"[{market}] {start}-{end} 早于 10 年窗口（起点 {min_date}），无法刷新"
                    )
                if not _covers(intervals, start, end):
                    raise CalendarOutOfRange(
                        f"[{market}] {start}-{end} 早于 10 年窗口（起点 {min_date}）且无缓存"
                    )
                self._mark(market, "cache", False, _fetched_at_for(intervals, start, end))
                return frame
            if start < min_date:
                if not _covers(intervals, start, min_date - timedelta(days=1)):
                    raise CalendarOutOfRange(
                        f"[{market}] {start} 早于 10 年窗口（起点 {min_date}）且无缓存"
                    )
                hist_start = min_date

            # 未来侧：整段越界直接报错
            if hist_start > max_date and not _covers(intervals, hist_start, end):
                raise CalendarFutureUnavailable(
                    f"[{market}] {hist_start} 超出可发布窗口（截止 {max_date}）"
                )

            clamped_end = end
            if end > max_date:
                logger.warning(
                    "[%s] 请求结束日 %s 超出今年 12/31，夹取到 %s", market, end, max_date
                )
                clamped_end = max_date

            missing = _missing_workdays(intervals, hist_start, clamped_end)
            stale = False
            if not refresh and self._intersects_current_year(hist_start, clamped_end, today):
                stale = self._current_year_stale(intervals, hist_start, clamped_end, today)

            if not missing and not stale and not refresh:
                self._mark(
                    market, "cache", False, _fetched_at_for(intervals, hist_start, clamped_end)
                )
                return frame

            right = _coverage_right(intervals)

            # 先判 coverage：已确认前缀内可返回时，不因未来未发布而回源。
            # 边界必须是 today，不能是 coverage 的 right——否则 2–11 月这类
            # 历史缺口会被误判成「未来未发布」，一次 futu 都不请求。
            if (
                missing
                and not refresh
                and not stale
                and right is not None
                and hist_start <= right
                and all(gap_start >= today for gap_start, _ in missing)
            ):
                if allow_partial:
                    logger.warning("[%s] 未来日历未发布，返回已覆盖部分（截至 %s）", market, right)
                    self._mark(
                        market, "cache", False, _fetched_at_for(intervals, hist_start, clamped_end)
                    )
                    return frame
                raise CalendarFutureUnavailable(
                    f"[{market}] {hist_start}-{clamped_end} 超出已确认 coverage（截至 {right}）"
                )

            # 再判负缓存（历史缺口不受负缓存约束）
            if missing and not refresh and self._probe_fresh(probe, today):
                if all(gap_start >= today for gap_start, _ in missing):
                    raise CalendarFutureUnavailable(
                        f"[{market}] 未来日历未发布（负缓存至 {probe.isoformat()}），暂不请求 futu"
                    )

            if self.client is None:
                if _covers(intervals, hist_start, clamped_end):
                    logger.warning("[%s] 无 futu client，回退旧缓存", market)
                    self._mark(
                        market, "cache", True, _fetched_at_for(intervals, hist_start, clamped_end)
                    )
                    return frame
                raise CalendarUnavailable(f"[{market}] 无 futu client 且缓存未覆盖")

            force_range: Optional[Tuple[date, date]] = None
            if refresh:
                force_range = (hist_start, clamped_end)
            elif stale:
                year_start = max(hist_start, date(today.year, 1, 1))
                year_end = min(clamped_end, date(today.year, 12, 31))
                if year_start <= year_end:
                    force_range = (year_start, year_end)

            # 最后回源
            try:
                frame, intervals, probe = self._fetch_missing(
                    market,
                    hist_start,
                    clamped_end,
                    frame,
                    intervals,
                    probe,
                    today,
                    max_date,
                    min_date,
                    clear_probe=refresh or prewarming,
                    force_range=force_range,
                )
            except (CalendarFutureUnavailable, CalendarOutOfRange):
                raise
            except Exception as exc:  # noqa: BLE001 - 限流/窗口空洞也走缓存回退
                if _covers(intervals, hist_start, clamped_end):
                    logger.warning("[%s] futu 不可用，回退旧缓存: %s", market, exc)
                    self._mark(
                        market, "cache", True, _fetched_at_for(intervals, hist_start, clamped_end)
                    )
                    return frame
                if isinstance(exc, CalendarError):
                    raise
                raise CalendarUnavailable(f"[{market}] futu 不可用且缓存未覆盖: {exc}") from exc

            remaining = _missing_workdays(intervals, hist_start, clamped_end)
            if remaining:
                right = _coverage_right(intervals)
                future_only = all(gap_start >= today for gap_start, _ in remaining)
                if future_only:
                    has_prefix = right is not None and hist_start <= right
                    if allow_partial and has_prefix:
                        logger.warning(
                            "[%s] 未来日历未发布，返回已覆盖部分（截至 %s）", market, right
                        )
                        self._mark(
                            market,
                            "cache",
                            False,
                            _fetched_at_for(intervals, hist_start, clamped_end),
                        )
                        return frame
                    raise CalendarFutureUnavailable(
                        f"[{market}] {remaining[0][0]} 起未来日历未发布"
                        f"（已确认截至 {right if right is not None else today}）"
                    )
                raise CalendarUnavailable(
                    f"[{market}] 缓存仍有覆盖空洞：{remaining[:3]}"
                )

            self._mark(market, "futu", False)
            return frame

    def _fetch_missing(
        self,
        market: str,
        start: date,
        end: date,
        frame: pd.DataFrame,
        intervals: List[_Interval],
        probe: Optional[datetime],
        today: date,
        max_date: date,
        min_date: date,
        *,
        clear_probe: bool,
        force_range: Optional[Tuple[date, date]] = None,
    ) -> Tuple[pd.DataFrame, List[_Interval], Optional[datetime]]:
        missing = _missing_workdays(intervals, start, end)
        if force_range:
            # 强制回源与缺口取并集：refresh/prewarm/stale 必须重取已覆盖前缀，
            # 不能因为「与某个缺口重叠」就跳过。
            missing = _merge_ranges([*missing, force_range])
        rows: List[pd.DataFrame] = []
        intervals = list(intervals)
        write_rows = False

        for gap_start, gap_end in missing:
            # 未来侧一次拉到今年 12/31：否则"单日查休市"会返回空，无法区分
            # 「当天休市」与「未来日历未发布」（见 §7.3 已发布分支契约）。
            if gap_end > today:
                gap_end = max_date
            for chunk_start, chunk_end in _year_chunks(gap_start, gap_end):
                fetched = self._request(market, chunk_start, chunk_end)

                if fetched.empty:
                    if chunk_start > today:
                        if not clear_probe:
                            probe = self._now()
                        logger.warning(
                            "[%s] futu 对 %s-%s 返回空，视为未来日历未发布", market, chunk_start, chunk_end
                        )
                        continue
                    if chunk_end > today:
                        # 区间跨今天却一条都没有：无法判断，按不可用处理
                        raise CalendarUnavailable(
                            f"[{market}] futu 对 {chunk_start}-{chunk_end} 返回空"
                        )
                    # 纯历史 chunk 返回空：用所在自然年做宽范围复核，
                    # 区分「整段休市」与「服务端异常/限流后的空结果」。
                    wide = self._recheck_chunk(
                        market, chunk_start, chunk_end, min_date, max_date
                    )
                    if wide is None:
                        raise CalendarUnavailable(
                            f"[{market}] futu 对 {chunk_start}-{chunk_end} 及其所在年份均返回空，"
                            "无法确认休市"
                        )
                    dates = wide["date"].dt.date
                    inside = wide.loc[(dates >= chunk_start) & (dates <= chunk_end)]
                    if not inside.empty:
                        rows.append(inside)
                    intervals = _add_interval(intervals, chunk_start, chunk_end, self._now())
                    write_rows = True
                    continue

                rows.append(fetched)
                write_rows = True
                dates = fetched["date"].dt.date
                has_future = bool((dates > today).any())

                if chunk_end <= today:
                    intervals = _add_interval(intervals, chunk_start, chunk_end, self._now())
                    continue

                if has_future:
                    right = min(chunk_end, max_date)
                    intervals = _add_interval(intervals, chunk_start, right, self._now())
                    probe = None
                else:
                    last_day = dates.max()
                    confirmed = max(
                        (item.end for item in intervals if item.start <= chunk_end and item.end >= chunk_start),
                        default=None,
                    )
                    right = max(filter(lambda item: item is not None, (confirmed, last_day)))
                    if right >= chunk_start:
                        intervals = _add_interval(intervals, chunk_start, min(right, chunk_end), self._now())
                    if not clear_probe:
                        probe = self._now()

        if rows:
            frame = pd.concat([frame, *rows], ignore_index=True)
            frame = frame.drop_duplicates(subset=["date"], keep="last")
            frame = frame.sort_values("date").reset_index(drop=True)

        if clear_probe:
            probe = None

        if write_rows:
            frame, intervals, probe = self._store.write(
                market, frame, intervals, probe, write_rows=True
            )
        elif clear_probe or probe != self._probes.get(market):
            frame, intervals, probe = self._store.write(
                market, frame, intervals, probe, write_rows=False
            )

        self._frames[market] = frame
        self._intervals[market] = intervals
        self._probes[market] = probe
        return frame, intervals, probe

    def _recheck_chunk(
        self,
        market: str,
        chunk_start: date,
        chunk_end: date,
        min_date: date,
        max_date: date,
    ) -> Optional[pd.DataFrame]:
        """历史空返回复核：请求 chunk 所在自然年（裁剪到可取窗口）。

        宽请求仍为空 → 返回 None（调用方抛 CalendarUnavailable，不写盘）；
        chunk 自身就是整年时也无处复核，返回 None。
        """
        wide_start = max(date(chunk_start.year, 1, 1), min_date)
        wide_end = min(date(chunk_start.year, 12, 31), max_date)
        if wide_start > wide_end or (wide_start, wide_end) == (chunk_start, chunk_end):
            return None
        wide = self._request(market, wide_start, wide_end)
        return None if wide.empty else wide

    def _request(self, market: str, start: date, end: date) -> pd.DataFrame:
        last_error: Optional[Exception] = None
        attempts = max(1, len(self.retry_backoff) + 1)
        for attempt in range(attempts):
            if attempt:
                _time.sleep(self.retry_backoff[attempt - 1])
            try:
                self.rate_limiter.acquire()
                return normalize_trading_days_payload(
                    self.client.get_trading_days(
                        market, start.isoformat(), end.isoformat()
                    ),
                    market,
                )
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                if not _is_rate_limited(exc):
                    raise
        raise CalendarRateLimited(f"[{market}] 限流重试 {attempts} 次仍失败: {last_error}") from last_error

    # -- 内部：override ---------------------------------------------------- #
    def _validated_overrides(
        self, market: str, frame: pd.DataFrame
    ) -> Dict[date, Tuple[dtime, Optional[str], Optional[str]]]:
        rows = _read_override_rows(self.overrides_dir / market / "overrides.csv", market)
        if not rows:
            return {}

        session_map = dict(zip(frame["date"].dt.date, frame["session_type"]))
        result: Dict[date, Tuple[dtime, Optional[str], Optional[str]]] = {}
        for day, close_time, source, note in rows:
            if day in result:
                self._warn_once(f"{market}:{day}:dup", f"[{market}] override 重复日期 {day}，保留第一条")
                continue
            session_type = session_map.get(day)
            if session_type is None:
                self._warn_once(f"{market}:{day}:holiday", f"[{market}] override {day} 非交易日，已忽略")
                continue
            segments = _segments_for(market, session_type)
            seg_start, seg_end = segments[-1]
            if not (seg_start < close_time < seg_end):
                self._warn_once(
                    f"{market}:{day}:range",
                    f"[{market}] override {day} close_time={close_time} 不在 {session_type} 时段内，已忽略",
                )
                continue
            result[day] = (close_time, source, note)
        return result

    def _warn_once(self, key: str, message: str) -> None:
        if key not in self._warned_overrides:
            self._warned_overrides.add(key)
            logger.warning(message)


def _read_override_rows(
    path: Path, market: str
) -> List[Tuple[date, dtime, Optional[str], Optional[str]]]:
    if not path.exists():
        return []
    rows: List[Tuple[date, dtime, Optional[str], Optional[str]]] = []
    try:
        with open(path, "r", encoding="utf-8-sig", newline="") as handle:
            for raw in csv.DictReader(handle):
                raw_day = (raw.get("date") or "").strip()
                raw_close = (raw.get("close_time") or "").strip()
                if not raw_day or not raw_close:
                    logger.warning("[%s] override 行缺少 date/close_time，已忽略: %r", market, raw)
                    continue
                try:
                    day = date.fromisoformat(raw_day)
                except ValueError:
                    logger.warning("[%s] override 日期非法，已忽略: %r", market, raw_day)
                    continue
                match = _CLOSE_TIME_RE.match(raw_close)
                if not match:
                    logger.warning("[%s] override close_time 非法，已忽略: %r", market, raw_close)
                    continue
                close_time = dtime(int(match.group(1)), int(match.group(2)))
                rows.append(
                    (
                        day,
                        close_time,
                        (raw.get("source") or "").strip() or None,
                        (raw.get("note") or "").strip() or None,
                    )
                )
    except OSError as exc:
        logger.warning("[%s] override 读取失败: %s", market, exc)
    return rows


def _missing_workdays(
    intervals: Sequence[_Interval], start: date, end: date
) -> List[Tuple[date, date]]:
    """缺失区间里只保留工作日；周末是结构性休市。"""
    result: List[Tuple[date, date]] = []
    for gap_start, gap_end in _missing_ranges(intervals, start, end):
        workdays = [day for day in _date_range(gap_start, gap_end) if not _is_weekend(day)]
        if not workdays:
            continue
        result.append((workdays[0], workdays[-1]))
    return result


def _year_chunks(start: date, end: date) -> Iterator[Tuple[date, date]]:
    cursor = start
    while cursor <= end:
        chunk_end = min(date(cursor.year, 12, 31), end)
        yield cursor, chunk_end
        cursor = chunk_end + timedelta(days=1)


def _is_rate_limited(exc: Exception) -> bool:
    message = str(exc).lower()
    return any(token in message for token in ("frequency", "rate limit", "too many", "频繁", "超限", "限制"))
