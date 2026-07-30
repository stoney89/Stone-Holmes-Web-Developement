# MNQ Trading Toolkit

Research, detect, backtest, score, and journal MNQ (Micro E-mini Nasdaq-100)
day-trading setups. Built to support the plan in **[TRADING_PLAN.md](TRADING_PLAN.md)** —
read that first; the code exists to enforce it.

## What's here

| File | Purpose |
|---|---|
| `TRADING_PLAN.md` | The plan: setups, risk rules, paper-trading gates, financial route |
| `data.py` | Load TradingView CSV exports, yfinance NQ=F bars, or synthetic test data |
| `indicators.py` | VWAP, EMAs, ATR, PDH/PDL, opening range, swing pivots, FVGs |
| `setups.py` | Detectors: ORB, VWAP trend, PDH/PDL sweep, sweep→CHoCH |
| `backtest.py` | Conservative bar-by-bar backtester with real MNQ costs ($2/pt, commissions, slippage) |
| `run_backtest.py` | CLI that wires it all together |
| `scorer.py` | Pre-entry checklist that grades a trade A+/A/B/C |
| `journal_template.csv` + `journal.py` | Trade journal and expectancy analyzer |

## Quick start

```bash
pip install pandas numpy            # yfinance too, if you want Yahoo data

# 1. Prove the pipeline runs (synthetic data — numbers are meaningless)
python3 run_backtest.py --synthetic

# 2. Real quick look: ~60 days of NQ 5-minute bars from Yahoo
pip install yfinance
python3 run_backtest.py --yfinance

# 3. Best data: an OHLCV CSV — TradingView chart export (Premium plan) or
#    Databento (CME-licensed; $125 free signup credit covers years of
#    1-minute MNQ bars). Both formats are auto-detected.
python3 run_backtest.py --csv MNQ_5m.csv --trades-csv results.csv

# Grade a trade before you take it
python3 scorer.py

# Analyze your journal (copy journal_template.csv to my_journal.csv first)
python3 journal.py my_journal.csv
```

## Honest limitations

- Bar-based backtesting can't see intra-bar order; this engine assumes the
  **stop fills first** whenever a bar spans both stop and target, so results
  are biased *against* you. A strategy that survives that bias is worth
  forward-testing; one that doesn't isn't.
- yfinance gives ~60 days of 5m data — enough for a sanity check, not a
  verdict. Use TradingView exports (or paid data) for anything you'll act on.
- No backtest replaces the paper-trading gates in the plan. The backtest tells
  you a setup *can* have an edge; only forward execution tells you *you* do.
