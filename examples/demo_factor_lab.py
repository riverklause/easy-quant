"""factor_lab 端到端演示：真实港股日线 → 面板 → 因子 → RankIC。

诚实边界：
- 只有 10 只港股、日线，横截面很窄，IC 的噪声远大于均值；
- 本脚本证明"管线通了"（数据 → 面板 → 因子 → IC），**不证明任何因子有效**；
- `data/historical` 在 `.gitignore` 里，干净 clone 跑不了，因此不进 pytest。
"""

import logging
import sys
from contextlib import contextmanager
from pathlib import Path

import pandas as pd

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from research.factor_lab import factors
from research.factor_lab.cross_section import factor_correlation, paired_counts
from research.factor_lab.decay import ic_decay
from research.factor_lab.ic import ic_summary, rank_ic
from research.factor_lab.labels import forward_returns
from research.factor_lab.panel import to_panel

DATA_DIR = _ROOT / "data" / "historical" / "yfinance"
REQUIRED = ("open", "high", "low", "close", "volume")
HORIZON = 5
MIN_STOCKS = 5
HORIZONS = (1, 5, 10, 20)


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
        # 只取 close；旧文件 adj_close 用 0 占位，若要用它必须走 normalize_adj_close
        symbol, df = _normalize(pd.read_parquet(p), p.name)
        out[symbol] = df
    return out


@contextmanager
def _quiet_ic_logger():
    """丢弃数已进表格，日志不再逐条刷屏；退出时恢复调用方的级别。"""
    logger = logging.getLogger("research.factor_lab.ic")
    previous = logger.level
    logger.setLevel(logging.ERROR)
    try:
        yield
    finally:
        logger.setLevel(previous)


def main() -> None:
    bars = load_daily()
    close = to_panel(bars, "close")
    fwd = forward_returns(close, horizon=HORIZON)

    counts = (close.notna() & fwd.notna()).sum(axis=1)
    print(f"标的 {len(bars)} 只 | 交易日 {len(close)} | 前瞻 {HORIZON} 日")
    print(f"每日有效样本：中位数 {counts.median():.0f}，最小 {counts.min():.0f}"
          f"（min_stocks={MIN_STOCKS}）")
    print("drop = 因有效样本不足被丢弃的截面数（与日志 warning 同源，这里并入表格）")
    print(f"t     = IR * sqrt(n)（假设 iid，**高估**；前瞻 {HORIZON} 日重叠）")
    print(f"t_adj = t / sqrt({HORIZON})，用新息样本数校正；10 只股票下均不显著")
    print(f"ACTIVE = {', '.join(n.removesuffix('_factor') for n in factors.ACTIVE)}"
          "（相关 > 0.85 视为同一因子，每个维度只留一个代表）\n")

    header = (f"{'factor':22s} {'n':>4s} {'drop':>4s} {'meanIC':>8s} "
              f"{'std':>7s} {'IR':>7s} {'IC>0':>6s} {'t':>6s} {'t_adj':>7s}")
    print(header)
    print("-" * len(header))

    panels: dict[str, pd.DataFrame] = {}
    ics: dict[str, pd.Series] = {}
    with _quiet_ic_logger():
        for name in factors.__all__:
            panel = getattr(factors, name)(bars)
            panels[name] = panel                    # 矩阵要用全目录，做剪枝证据
            if name not in factors.ACTIVE:
                continue
            ic = rank_ic(panel, fwd, min_stocks=MIN_STOCKS)
            ics[name] = ic
            dropped = int((paired_counts(panel, fwd) < MIN_STOCKS).sum())
            s = ic_summary(ic)

            if s.n == 0:
                print(f"{name:22s} {0:4d} {dropped:4d} "
                      f"{'-':>8s} {'-':>7s} {'-':>7s} {'-':>6s} {'-':>6s} {'-':>7s}")
                continue

            print(f"{name:22s} {s.n:4d} {dropped:4d} {s.mean:+8.4f} {s.std:7.4f} "
                  f"{s.ir:+7.3f} {s.positive_ratio:6.0%} {s.t_stat:+6.2f} "
                  f"{s.t_stat / HORIZON ** 0.5:+7.2f}")

    common_n = len(set.intersection(*(set(ics[n].index) for n in ics)))
    print(f"\n共同评估窗口 n = {common_n}（warmup 不同导致各行的 n 不同，"
          "横向比 meanIC 时请以这一行为准）")

    corr = factor_correlation(panels, min_stocks=MIN_STOCKS)
    short = {name: name.removesuffix("_factor") for name in panels}
    print("\n因子互相关（全目录 9 个，剪枝证据；逐日截面 Spearman 均值。"
          "正负号跟着各自的原始刻度，RSI 与 WR 同号是正常的）")
    print(corr.matrix.rename(index=short, columns=short).round(2).to_string())
    mn, mx = int(corr.n.to_numpy().min()), int(corr.n.to_numpy().max())
    print(f"有效截面数 {mn}~{mx}：与总天数 {len(close)} 的差 = 被丢弃的截面 + 相关未定义的截面"
          "（后者在 rank_ic 里是静默丢的，这里由 n 暴露出来）")

    print(f"\nIC 衰减（horizon={HORIZONS}，单元格 = meanIC(n)；"
          "n 随 horizon 变小、窗口重叠，t 需按 sqrt(h) 折减）")
    header = f"{'factor':22s}" + "".join(f"{'h' + str(h):>13s}" for h in HORIZONS)
    print(header)
    print("-" * len(header))

    with _quiet_ic_logger():
        for name in factors.ACTIVE:
            decay = ic_decay(panels[name], close, horizons=HORIZONS,
                             min_stocks=MIN_STOCKS)
            cells = "".join(
                f"{row.mean_ic:+7.3f}({row.n:4d})" for row in decay.itertuples()
            )
            print(f"{name:22s}{cells}")

    print("\nIC 衰减（非重叠：每 h 个交易日取一个，n 即新息样本数）")
    with _quiet_ic_logger():
        for name in factors.ACTIVE:
            decay = ic_decay(panels[name], close, horizons=HORIZONS,
                             min_stocks=MIN_STOCKS, stride=True)
            rows = [f"{d.mean_ic:+7.3f}({d.n:3d})" for d in decay.itertuples()]
            print(f"{name:22s}" + "".join(f"{r:>13s}" for r in rows))


if __name__ == "__main__":
    main()
