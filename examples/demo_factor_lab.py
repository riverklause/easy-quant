"""factor_lab 端到端演示：真实港股日线 → 面板 → 因子 → RankIC。

诚实边界：
- 只有 10 只港股、日线，横截面很窄，IC 的噪声远大于均值；
- 本脚本证明"管线通了"（数据 → 面板 → 因子 → IC），**不证明任何因子有效**；
- `data/historical` 在 `.gitignore` 里，干净 clone 跑不了，因此不进 pytest。
"""

import sys
from pathlib import Path

import pandas as pd

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from research.factor_lab import factors
from research.factor_lab.ic import rank_ic
from research.factor_lab.labels import forward_returns
from research.factor_lab.panel import to_panel

DATA_DIR = _ROOT / "data" / "historical" / "yfinance"
REQUIRED = ("open", "high", "low", "close", "volume")
HORIZON = 5
MIN_STOCKS = 5


def _normalize(df: pd.DataFrame, name: str) -> tuple[str, pd.DataFrame]:
    """把原始 parquet 规整成 (symbol, OHLCV DataFrame with DatetimeIndex)。

    实跑 schema（与元数据扫描有出入）：
      index : MultiIndex(time_key datetime64[ms], code str)
      cols  : MultiIndex(level 0: 'Price' 等表头, level 1: open/high/low/close/volume/adj_close)
    """
    # 确认一文件一只 symbol
    codes = df.index.get_level_values("code").unique()
    if len(codes) != 1:
        raise SystemExit(f"{name}: 含多只 code {list(codes)}，预期单 symbol")
    symbol = codes[0]

    # 取 level 1 作为列名、丢弃顶层表头
    if isinstance(df.columns, pd.MultiIndex):
        df = df.droplevel(0, axis=1)

    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise SystemExit(f"{name} ({symbol}): 缺列 {missing}；实际列 {list(df.columns)}")

    out = df[list(REQUIRED)].copy()
    out.index = df.index.get_level_values("time_key")
    # 归一化到纯 Date（部分文件可能是带毫秒的 datetime）
    out.index = pd.to_datetime(out.index).normalize()
    return symbol, out.sort_index()


def load_daily() -> dict[str, pd.DataFrame]:
    if not DATA_DIR.exists():
        raise SystemExit(f"找不到 {DATA_DIR}（data/historical 在 .gitignore 里）")
    files = sorted(DATA_DIR.glob("HK_*_daily.parquet"))
    if not files:
        raise SystemExit(f"{DATA_DIR} 下没有 HK_*_daily.parquet")
    out = {}
    for p in files:
        symbol, df = _normalize(pd.read_parquet(p), p.name)
        out[symbol] = df
    return out


def main() -> None:
    bars = load_daily()
    close = to_panel(bars, "close")
    fwd = forward_returns(close, horizon=HORIZON)

    counts = (close.notna() & fwd.notna()).sum(axis=1)
    print(f"标的 {len(bars)} 只 | 交易日 {len(close)} | 前瞻 {HORIZON} 日")
    print(f"每日有效样本：中位数 {counts.median():.0f}，最小 {counts.min():.0f}"
          f"（min_stocks={MIN_STOCKS}）\n")

    header = f"{'factor':22s} {'n':>4s} {'meanIC':>8s} {'IR':>7s} {'IC>0':>6s}"
    print(header)
    print("-" * len(header))

    for name in factors.__all__:
        ic = rank_ic(getattr(factors, name)(bars), fwd, min_stocks=MIN_STOCKS)
        if ic.empty:
            print(f"{name:22s} {0:4d} {'-':>8s} {'-':>7s} {'-':>6s}")
            continue
        ir = ic.mean() / ic.std() if ic.std() else float("nan")
        print(f"{name:22s} {len(ic):4d} {ic.mean():+8.4f} {ir:+7.3f} "
              f"{(ic > 0).mean():6.0%}")


if __name__ == "__main__":
    main()
