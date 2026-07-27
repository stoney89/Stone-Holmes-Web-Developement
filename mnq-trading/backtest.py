"""Bar-by-bar backtester with realistic MNQ costs.

Fill model (deliberately conservative):
- Entry: next bar's open after the signal bar, plus slippage.
- Exit: stop or target, whichever the price path hits; if a single bar spans
  BOTH the stop and the target, the stop is assumed to fill first.
- Time stop: any open position exits at the 15:55 bar close.
- Costs: commission round-turn + slippage ticks on each side.

MNQ contract math: $2 per index point, 0.25 tick = $0.50.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import time

import numpy as np
import pandas as pd

from setups import Signal

POINT_VALUE = 2.0          # MNQ: $2 per point per contract
TICK = 0.25
COMMISSION_RT = 1.24       # typical all-in round-turn per MNQ contract
SLIPPAGE_TICKS = 1         # per side


@dataclass
class Trade:
    signal: Signal
    entry_time: pd.Timestamp
    entry: float
    exit_time: pd.Timestamp
    exit: float
    exit_reason: str        # "target" | "stop" | "eod"
    contracts: int
    points: float
    r_multiple: float
    pnl: float              # dollars, after costs


def run_backtest(df: pd.DataFrame, signals: list[Signal], contracts: int = 1,
                 max_trades_per_day: int = 4, one_at_a_time: bool = True,
                 eod: time = time(15, 55)) -> list[Trade]:
    trades: list[Trade] = []
    signals = sorted(signals, key=lambda s: s.time)
    busy_until: pd.Timestamp | None = None
    per_day: dict = {}

    idx = df.index
    slip = SLIPPAGE_TICKS * TICK

    for sig in signals:
        day = sig.time.date()
        if per_day.get(day, 0) >= max_trades_per_day:
            continue
        if one_at_a_time and busy_until is not None and sig.time < busy_until:
            continue
        pos = idx.searchsorted(sig.time, side="right")
        if pos >= len(idx) or idx[pos].date() != day:
            continue                                  # signal on the last bar of the day
        entry_time = idx[pos]
        entry_raw = df["open"].iloc[pos]
        long = sig.direction == "long"
        entry = entry_raw + slip if long else entry_raw - slip
        risk = (entry - sig.stop) if long else (sig.stop - entry)
        if risk <= 0:
            continue                                  # gap through the stop — no trade
        target = entry + sig.target_r * risk if long else entry - sig.target_r * risk

        exit_time, exit_px, reason = None, None, None
        j = pos
        while j < len(idx) and idx[j].date() == day:
            bar = df.iloc[j]
            hit_stop = bar["low"] <= sig.stop if long else bar["high"] >= sig.stop
            hit_tgt = bar["high"] >= target if long else bar["low"] <= target
            if hit_stop:                              # stop wins ties — conservative
                exit_time, reason = idx[j], "stop"
                exit_px = sig.stop - slip if long else sig.stop + slip
                break
            if hit_tgt:
                exit_time, reason = idx[j], "target"
                exit_px = target - slip if long else target + slip
                break
            if idx[j].time() >= eod:
                exit_time, reason = idx[j], "eod"
                exit_px = bar["close"] - slip if long else bar["close"] + slip
                break
            j += 1
        if exit_time is None:                         # data ended intraday
            exit_time, reason = idx[j - 1], "eod"
            last = df.iloc[j - 1]["close"]
            exit_px = last - slip if long else last + slip

        points = (exit_px - entry) if long else (entry - exit_px)
        pnl = points * POINT_VALUE * contracts - COMMISSION_RT * contracts
        trades.append(Trade(sig, entry_time, round(entry, 2), exit_time, round(exit_px, 2),
                            reason, contracts, round(points, 2),
                            round(points / risk, 2), round(pnl, 2)))
        per_day[day] = per_day.get(day, 0) + 1
        busy_until = exit_time
    return trades


def summarize(trades: list[Trade]) -> dict:
    if not trades:
        return {"trades": 0}
    pnl = np.array([t.pnl for t in trades])
    rs = np.array([t.r_multiple for t in trades])
    wins, losses = pnl[pnl > 0], pnl[pnl <= 0]
    equity = np.cumsum(pnl)
    drawdown = equity - np.maximum.accumulate(equity)
    days = len({t.entry_time.date() for t in trades})
    return {
        "trades": len(trades),
        "days": days,
        "win_rate": round(len(wins) / len(trades) * 100, 1),
        "avg_R": round(rs.mean(), 2),
        "expectancy_$": round(pnl.mean(), 2),
        "profit_factor": round(wins.sum() / abs(losses.sum()), 2) if losses.sum() != 0 else float("inf"),
        "total_$": round(pnl.sum(), 2),
        "max_drawdown_$": round(drawdown.min(), 2),
        "avg_$_per_day": round(pnl.sum() / days, 2),
        "best_$": round(pnl.max(), 2),
        "worst_$": round(pnl.min(), 2),
    }


def summarize_by_setup(trades: list[Trade]) -> pd.DataFrame:
    rows = {}
    for name in sorted({t.signal.setup for t in trades}):
        rows[name] = summarize([t for t in trades if t.signal.setup == name])
    return pd.DataFrame(rows).T


def trades_to_frame(trades: list[Trade]) -> pd.DataFrame:
    return pd.DataFrame([{
        "entry_time": t.entry_time, "setup": t.signal.setup, "dir": t.signal.direction,
        "entry": t.entry, "stop": t.signal.stop, "exit": t.exit, "reason": t.exit_reason,
        "R": t.r_multiple, "pnl_$": t.pnl,
    } for t in trades])
