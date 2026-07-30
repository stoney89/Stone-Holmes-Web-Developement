"""Run the full pipeline: load data -> enrich -> detect setups -> backtest -> report.

Examples:
    # smoke test on synthetic data (numbers are meaningless, proves the code runs)
    python3 run_backtest.py --synthetic

    # real data from a TradingView export (chart -> ... -> Export chart data)
    python3 run_backtest.py --csv MNQ_5m.csv

    # free Yahoo data: ~60 days of 5-minute NQ bars
    python3 run_backtest.py --yfinance

    # single setup only
    python3 run_backtest.py --yfinance --setups orb vwap_trend
"""

from __future__ import annotations

import argparse

import pandas as pd

import data as data_mod
from backtest import run_backtest, summarize, summarize_by_setup, trades_to_frame
from indicators import enrich
from setups import ALL_SETUPS


def main() -> None:
    p = argparse.ArgumentParser(description="MNQ setup backtester")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--csv", help="OHLCV CSV export (TradingView, Databento, etc.)")
    src.add_argument("--yfinance", action="store_true", help="fetch NQ=F 5m bars from Yahoo")
    src.add_argument("--synthetic", action="store_true", help="synthetic bars (pipeline test only)")
    p.add_argument("--setups", nargs="+", choices=list(ALL_SETUPS), default=list(ALL_SETUPS))
    p.add_argument("--contracts", type=int, default=1)
    p.add_argument("--max-per-day", type=int, default=4)
    p.add_argument("--trades-csv", help="write the trade list to this CSV")
    args = p.parse_args()

    if args.csv:
        df, source = data_mod.load_csv(args.csv), args.csv
    elif args.yfinance:
        df, source = data_mod.load_yfinance(), "yfinance NQ=F 5m"
    else:
        df, source = data_mod.synthetic_mnq(), "SYNTHETIC (results are meaningless)"

    df = data_mod.rth_only(df)
    df = enrich(df)
    print(f"Data: {source}  |  {len(df)} bars  |  "
          f"{df.index[0]:%Y-%m-%d} -> {df.index[-1]:%Y-%m-%d}\n")

    signals = []
    for name in args.setups:
        signals.extend(ALL_SETUPS[name](df))
    trades = run_backtest(df, signals, contracts=args.contracts,
                          max_trades_per_day=args.max_per_day)

    if not trades:
        print("No trades generated.")
        return

    pd.set_option("display.width", 140)
    print("=== Overall (1 contract unless --contracts) ===")
    for k, v in summarize(trades).items():
        print(f"  {k:>16}: {v}")
    print("\n=== By setup ===")
    print(summarize_by_setup(trades).to_string())

    frame = trades_to_frame(trades)
    print(f"\n=== Last 10 trades ===\n{frame.tail(10).to_string(index=False)}")
    if args.trades_csv:
        frame.to_csv(args.trades_csv, index=False)
        print(f"\nTrade list written to {args.trades_csv}")

    if args.synthetic:
        print("\n*** SYNTHETIC DATA — these numbers prove the pipeline runs, nothing else. ***")


if __name__ == "__main__":
    main()
