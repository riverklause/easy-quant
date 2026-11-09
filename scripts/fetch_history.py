"""批量抓取历史 K 线到 data/historical/{source}/{symbol}_{period}.parquet。

用法：
    python scripts/fetch_history.py --start 2024-01-01 --end 2024-12-31 --limit 20 --dry-run
    python scripts/fetch_history.py --start 2024-01-01 --end 2024-12-31 --limit 20

护栏：
- 分批 + 间隔，避免打爆 OpenD；
- 断点续跑：目标文件已存在则跳过；
- 缺失标的由 DataManager.get_batch_data 统一 warning（DM4a），脚本只汇总 N/M，不自造第二份计数。
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
from pathlib import Path

import pandas as pd

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from data.data_manager import DataManager
from data.storage.local_storage import LocalStorageManager


def load_symbols(args) -> list[str]:
    if args.symbols:
        return [s.strip() for s in args.symbols.split(",") if s.strip()]
    if args.symbols_file:
        text = Path(args.symbols_file).read_text(encoding="utf-8")
        return [
            line.split("#")[0].strip()
            for line in text.splitlines()
            if line.split("#")[0].strip()
        ]
    stock_list = LocalStorageManager().build_meta_path("StockList")
    if not stock_list.exists():
        raise SystemExit(f"找不到 {stock_list}；请用 --symbols 或 --symbols-file")
    return [str(c) for c in pd.read_parquet(stock_list)["code"].tolist()]


def target_path(storage: LocalStorageManager, symbol: str, source: str, period: str) -> Path:
    return storage.build_path(
        category="historical", symbol=symbol, source=source, period=period
    )


def main() -> int:
    p = argparse.ArgumentParser(description="批量抓取历史 K 线")
    p.add_argument("--source", default="futu")
    p.add_argument("--period", default="daily")
    p.add_argument("--start", required=True)
    p.add_argument("--end", required=True)
    p.add_argument("--symbols", help="逗号分隔，如 HK.00700,US.AAPL")
    p.add_argument("--symbols-file", help="每行一个代码")
    p.add_argument("--limit", type=int, default=0, help="只处理前 N 只（0=全部）")
    p.add_argument("--batch-size", type=int, default=50)
    p.add_argument("--sleep", type=float, default=1.0, help="批次间隔秒")
    p.add_argument("--adjusted", action="store_true")
    p.add_argument("--dry-run", action="store_true", help="只打印计划，不取数")
    args = p.parse_args()

    storage = LocalStorageManager()
    symbols = load_symbols(args)
    if args.limit:
        symbols = symbols[: args.limit]

    done = {
        s for s in symbols
        if target_path(storage, s, args.source, args.period).exists()
    }
    pending = [s for s in symbols if s not in done]

    print(f"请求 {len(symbols)} 只 | 已存在 {len(done)} | 待抓 {len(pending)}")
    if args.dry_run:
        print("示例待抓:", pending[:10])
        return 0
    if not pending:
        return 0

    dm = DataManager()
    if not dm.connect_all():
        raise SystemExit("数据源连接失败（OpenD 是否已启动？）")

    fetched: list[str] = []
    missing: list[str] = []
    failed_batches = 0

    for idx in range(0, len(pending), args.batch_size):
        batch = pending[idx : idx + args.batch_size]
        try:
            data = asyncio.run(
                dm.get_batch_data(
                    batch, args.source, args.start, args.end,
                    adjusted=args.adjusted, period=args.period,
                )
            )
        except Exception:
            failed_batches += 1
            print(f"批次 {idx // args.batch_size + 1}: 失败（已跳过）")
            continue

        for symbol, frame in data.items():
            if storage.save_data(
                frame, symbol,
                data_type=f"historical_{args.period}",
                source=args.source,
            ):
                fetched.append(symbol)
        missing.extend(s for s in batch if s not in data)

        print(f"批次 {idx // args.batch_size + 1}: 请求 {len(batch)} 成功 {len(data)}")
        time.sleep(args.sleep)

    print(
        f"\n汇总：待抓 {len(pending)} | 落盘 {len(fetched)} | "
        f"缺失 {len(missing)} | 失败批次 {failed_batches}"
    )
    if missing:
        print("缺失前 10:", missing[:10])
    return 0 if not (missing or failed_batches) else 1


if __name__ == "__main__":
    raise SystemExit(main())
