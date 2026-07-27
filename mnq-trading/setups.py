"""Setup detectors.

Each detector scans an enriched DataFrame (see indicators.enrich) and returns
a list of Signal objects. Detectors only use information available at signal
time — entries fill on the *next* bar's open in the backtester, so there is no
lookahead bias.

Implemented setups (all long/short symmetric):
  orb          Opening Range Breakout with retest-or-momentum entry
  vwap_trend   VWAP + EMA trend continuation on a pullback
  pdhl_sweep   Previous-day high/low liquidity sweep reversal
  sweep_choch  Liquidity sweep followed by a change of character (structure
               break against the sweep) — the "A+" ICT-style setup
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import time

import numpy as np
import pandas as pd


@dataclass
class Signal:
    time: pd.Timestamp          # bar on which the signal fired (entry = next bar open)
    setup: str
    direction: str              # "long" | "short"
    stop: float                 # protective stop price
    target_r: float = 2.0       # take-profit as a multiple of risk
    context: dict = field(default_factory=dict)


TRADE_START = time(9, 45)       # never trade the opening range itself
TRADE_END = time(15, 0)         # no new entries in the last hour
LUNCH_START, LUNCH_END = time(11, 30), time(13, 30)


def _in_window(ts: pd.Timestamp, avoid_lunch: bool = True) -> bool:
    t = ts.time()
    if not (TRADE_START <= t <= TRADE_END):
        return False
    if avoid_lunch and LUNCH_START <= t <= LUNCH_END:
        return False
    return True


def orb_signals(df: pd.DataFrame, buffer_points: float = 2.0, max_per_day: int = 1) -> list[Signal]:
    """Opening Range Breakout.

    Long when a bar *closes* above the opening-range high by `buffer_points`
    (close-based filter rejects single-tick fakeouts). Stop at the range
    midpoint. One breakout per direction per day, entries 9:45-11:30 only —
    ORB edge decays fast after the first 2 hours.
    """
    signals: list[Signal] = []
    for day, d in df.groupby(df.index.date):
        taken = {"long": 0, "short": 0}
        for ts, row in d.iterrows():
            if not (TRADE_START <= ts.time() <= time(11, 30)):
                continue
            if np.isnan(row["orh"]):
                continue
            mid = (row["orh"] + row["orl"]) / 2
            if taken["long"] < max_per_day and row["close"] > row["orh"] + buffer_points:
                signals.append(Signal(ts, "orb", "long", stop=mid,
                                      context={"orh": row["orh"], "orl": row["orl"]}))
                taken["long"] += 1
            elif taken["short"] < max_per_day and row["close"] < row["orl"] - buffer_points:
                signals.append(Signal(ts, "orb", "short", stop=mid,
                                      context={"orh": row["orh"], "orl": row["orl"]}))
                taken["short"] += 1
    return signals


def vwap_trend_signals(df: pd.DataFrame, atr_buffer: float = 0.5) -> list[Signal]:
    """VWAP trend continuation.

    Regime filter: price above VWAP and 9EMA > 20EMA -> longs only (mirror for
    shorts). Trigger: price pulls back to touch the 20EMA or VWAP, then a bar
    closes back above the 9EMA. Stop under the pullback low minus an ATR
    buffer. Skips lunch chop.
    """
    signals: list[Signal] = []
    for day, d in df.groupby(df.index.date):
        pulled_back_long = pulled_back_short = False
        pullback_low, pullback_high = np.inf, -np.inf
        last_entry_bar = None
        for ts, row in d.iterrows():
            if np.isnan(row["ema20"]) or np.isnan(row["atr"]):
                continue
            up = row["close"] > row["vwap"] and row["ema9"] > row["ema20"]
            down = row["close"] < row["vwap"] and row["ema9"] < row["ema20"]
            if up:
                pulled_back_short, pullback_high = False, -np.inf
                if row["low"] <= max(row["ema20"], row["vwap"]):
                    pulled_back_long = True
                    pullback_low = min(pullback_low, row["low"])
                elif pulled_back_long and row["close"] > row["ema9"] and _in_window(ts):
                    if last_entry_bar is None or (ts - last_entry_bar) > pd.Timedelta(minutes=30):
                        signals.append(Signal(ts, "vwap_trend", "long",
                                              stop=pullback_low - atr_buffer * row["atr"],
                                              context={"vwap": round(row["vwap"], 2)}))
                        last_entry_bar = ts
                    pulled_back_long, pullback_low = False, np.inf
            elif down:
                pulled_back_long, pullback_low = False, np.inf
                if row["high"] >= min(row["ema20"], row["vwap"]):
                    pulled_back_short = True
                    pullback_high = max(pullback_high, row["high"])
                elif pulled_back_short and row["close"] < row["ema9"] and _in_window(ts):
                    if last_entry_bar is None or (ts - last_entry_bar) > pd.Timedelta(minutes=30):
                        signals.append(Signal(ts, "vwap_trend", "short",
                                              stop=pullback_high + atr_buffer * row["atr"],
                                              context={"vwap": round(row["vwap"], 2)}))
                        last_entry_bar = ts
                    pulled_back_short, pullback_high = False, -np.inf
            else:
                pulled_back_long = pulled_back_short = False
                pullback_low, pullback_high = np.inf, -np.inf
    return signals


def pdhl_sweep_signals(df: pd.DataFrame, reject_within_bars: int = 3,
                       atr_buffer: float = 0.25) -> list[Signal]:
    """Previous-day high/low sweep reversal.

    Price trades beyond PDH (or PDL), then closes back inside within
    `reject_within_bars` bars -> fade it. Stop beyond the sweep extreme.
    One attempt per level per day.
    """
    signals: list[Signal] = []
    for day, d in df.groupby(df.index.date):
        state = {"pdh": None, "pdl": None}      # None -> "sweeping" ts -> "done"
        extreme = {"pdh": -np.inf, "pdl": np.inf}
        count = {"pdh": 0, "pdl": 0}
        for ts, row in d.iterrows():
            if np.isnan(row["pdh"]) or np.isnan(row["atr"]):
                continue
            # --- PDH side (potential short) ---
            if state["pdh"] is None and row["high"] > row["pdh"]:
                state["pdh"] = "sweeping"
            if state["pdh"] == "sweeping":
                extreme["pdh"] = max(extreme["pdh"], row["high"])
                count["pdh"] += 1
                if row["close"] < row["pdh"] and _in_window(ts, avoid_lunch=False):
                    if count["pdh"] <= reject_within_bars:
                        signals.append(Signal(ts, "pdhl_sweep", "short",
                                              stop=extreme["pdh"] + atr_buffer * row["atr"],
                                              context={"level": "PDH", "price": row["pdh"]}))
                    state["pdh"] = "done"
                elif count["pdh"] > reject_within_bars:
                    state["pdh"] = "done"       # accepted above the level, no fade
            # --- PDL side (potential long) ---
            if state["pdl"] is None and row["low"] < row["pdl"]:
                state["pdl"] = "sweeping"
            if state["pdl"] == "sweeping":
                extreme["pdl"] = min(extreme["pdl"], row["low"])
                count["pdl"] += 1
                if row["close"] > row["pdl"] and _in_window(ts, avoid_lunch=False):
                    if count["pdl"] <= reject_within_bars:
                        signals.append(Signal(ts, "pdhl_sweep", "long",
                                              stop=extreme["pdl"] - atr_buffer * row["atr"],
                                              context={"level": "PDL", "price": row["pdl"]}))
                    state["pdl"] = "done"
                elif count["pdl"] > reject_within_bars:
                    state["pdl"] = "done"
    return signals


def sweep_choch_signals(df: pd.DataFrame, choch_within_bars: int = 12,
                        atr_buffer: float = 0.25) -> list[Signal]:
    """Liquidity sweep -> CHoCH (change of character) entry.

    1. Price sweeps PDH/PDL or the pre-9:30 overnight high/low.
    2. Within `choch_within_bars` bars, price breaks the most recent
       *confirmed* swing in the opposite direction (the CHoCH).
    3. Enter on the CHoCH-breaking close; stop beyond the sweep extreme.

    This is the mechanical core of the sweep->CHoCH->BOS->FVG playbook; the
    retrace-into-FVG refinement is left for discretionary execution because
    it fills rarely enough to starve a backtest on limited data.
    """
    signals: list[Signal] = []
    for day, d in df.groupby(df.index.date):
        on = d.between_time("00:00", "09:29")
        onh = on["high"].max() if len(on) else np.nan
        onl = on["low"].min() if len(on) else np.nan
        last_swing_low = last_swing_high = np.nan
        sweep = None    # (direction_to_trade, extreme, bars_left, level_name)
        for ts, row in d.iterrows():
            if not np.isnan(row["swing_low"]):
                last_swing_low = row["swing_low"]
            if not np.isnan(row["swing_high"]):
                last_swing_high = row["swing_high"]
            if np.isnan(row["atr"]):
                continue
            highs = [x for x in (row["pdh"], onh) if not np.isnan(x)]
            lows = [x for x in (row["pdl"], onl) if not np.isnan(x)]
            if sweep is None:
                for lvl in highs:
                    if row["high"] > lvl:
                        sweep = ["short", row["high"], choch_within_bars,
                                 "PDH" if lvl == row["pdh"] else "ONH"]
                        break
                if sweep is None:
                    for lvl in lows:
                        if row["low"] < lvl:
                            sweep = ["long", row["low"], choch_within_bars,
                                     "PDL" if lvl == row["pdl"] else "ONL"]
                            break
            else:
                direction, extreme, bars_left, level = sweep
                extreme = max(extreme, row["high"]) if direction == "short" else min(extreme, row["low"])
                bars_left -= 1
                fired = False
                if direction == "short" and not np.isnan(last_swing_low) and row["close"] < last_swing_low:
                    if _in_window(ts, avoid_lunch=False):
                        signals.append(Signal(ts, "sweep_choch", "short",
                                              stop=extreme + atr_buffer * row["atr"],
                                              context={"swept": level, "choch_at": last_swing_low}))
                    fired = True
                elif direction == "long" and not np.isnan(last_swing_high) and row["close"] > last_swing_high:
                    if _in_window(ts, avoid_lunch=False):
                        signals.append(Signal(ts, "sweep_choch", "long",
                                              stop=extreme - atr_buffer * row["atr"],
                                              context={"swept": level, "choch_at": last_swing_high}))
                    fired = True
                sweep = None if (fired or bars_left <= 0) else [direction, extreme, bars_left, level]
    return signals


ALL_SETUPS = {
    "orb": orb_signals,
    "vwap_trend": vwap_trend_signals,
    "pdhl_sweep": pdhl_sweep_signals,
    "sweep_choch": sweep_choch_signals,
}
