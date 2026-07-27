"""Journal analyzer — the feedback loop that actually makes you better.

Fill journal_template.csv (one row per trade, including skipped C setups with
0 contracts) and run:

    python3 journal.py my_journal.csv

It reports expectancy by setup, by grade, by session window, and by
rule-following — so after 30-50 paper trades you can see, in numbers, which
setup deserves your size and which should be cut.
"""

from __future__ import annotations

import sys

import pandas as pd


def _table(df: pd.DataFrame, by: str) -> pd.DataFrame:
    g = df.groupby(by)
    out = pd.DataFrame({
        "trades": g.size(),
        "win_rate_%": (g["pnl_usd"].apply(lambda s: (s > 0).mean() * 100)).round(1),
        "avg_R": g["actual_r"].mean().round(2),
        "expectancy_$": g["pnl_usd"].mean().round(2),
        "total_$": g["pnl_usd"].sum().round(2),
    })
    return out.sort_values("expectancy_$", ascending=False)


def main(path: str) -> None:
    df = pd.read_csv(path)
    df = df[df["contracts"] > 0]        # skipped setups logged with 0 contracts
    if df.empty:
        print("No executed trades in the journal yet.")
        return
    df["pnl_usd"] = pd.to_numeric(df["pnl_usd"], errors="coerce").fillna(0)
    df["actual_r"] = pd.to_numeric(df["actual_r"], errors="coerce")

    print(f"Executed trades: {len(df)}   Total P&L: ${df['pnl_usd'].sum():,.2f}\n")
    for col, title in [("setup", "By setup"), ("grade_before_entry", "By pre-entry grade"),
                       ("session_window", "By session"), ("followed_plan", "Followed plan?")]:
        if col in df.columns and df[col].notna().any():
            print(f"=== {title} ===")
            print(_table(df, col).to_string(), "\n")

    if "mistake_tags" in df.columns:
        tags = df["mistake_tags"].dropna().astype(str)
        tags = tags[tags.str.strip() != ""]
        if len(tags):
            counts = tags.str.split(";").explode().str.strip().value_counts()
            print("=== Most common mistakes ===")
            print(counts.head(10).to_string())


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: python3 journal.py <journal.csv>")
        sys.exit(1)
    main(sys.argv[1])
