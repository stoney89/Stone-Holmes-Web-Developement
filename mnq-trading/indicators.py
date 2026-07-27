"""Indicators and session levels used by the setup detectors.

Everything operates on a DataFrame indexed by tz-aware ET timestamps with
open/high/low/close/volume columns (see data.py).
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def ema(series: pd.Series, length: int) -> pd.Series:
    return series.ewm(span=length, adjust=False).mean()


def atr(df: pd.DataFrame, length: int = 14) -> pd.Series:
    prev_close = df["close"].shift(1)
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - prev_close).abs(),
        (df["low"] - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / length, adjust=False).mean()


def session_vwap(df: pd.DataFrame) -> pd.Series:
    """VWAP anchored to each session date (resets daily)."""
    typical = (df["high"] + df["low"] + df["close"]) / 3
    pv = typical * df["volume"]
    day = df.index.date
    cum_pv = pv.groupby(day).cumsum()
    cum_v = df["volume"].groupby(day).cumsum().replace(0, np.nan)
    vwap = cum_pv / cum_v
    return vwap.fillna(typical)


def daily_levels(df: pd.DataFrame) -> pd.DataFrame:
    """Per-bar previous-day high/low (PDH/PDL), computed from RTH bars.

    If the frame includes overnight bars, PDH/PDL still use only 9:30-16:00 ET.
    """
    rth = df.between_time("09:30", "15:59")
    daily = rth.groupby(rth.index.date).agg(pdh=("high", "max"), pdl=("low", "min"))
    daily.index = pd.to_datetime(daily.index)
    prev = daily.shift(1)
    dates = pd.to_datetime(pd.Series(df.index.date, index=df.index))
    out = pd.DataFrame(index=df.index)
    out["pdh"] = dates.map(prev["pdh"])
    out["pdl"] = dates.map(prev["pdl"])
    return out


def opening_range(df: pd.DataFrame, minutes: int = 15) -> pd.DataFrame:
    """Per-bar opening-range high/low (first `minutes` from 9:30 ET).

    Bars inside the opening range get NaN so no strategy trades the range
    while it is still forming.
    """
    end = (pd.Timestamp("09:30") + pd.Timedelta(minutes=minutes)).time()
    orb = df.between_time("09:30", end, inclusive="left")
    ranges = orb.groupby(orb.index.date).agg(orh=("high", "max"), orl=("low", "min"))
    dates = pd.Series(df.index.date, index=df.index)
    out = pd.DataFrame(index=df.index)
    out["orh"] = dates.map(ranges["orh"])
    out["orl"] = dates.map(ranges["orl"])
    formed = pd.Series(df.index.time, index=df.index) >= end
    out.loc[~formed, ["orh", "orl"]] = np.nan
    return out


def swing_pivots(df: pd.DataFrame, left: int = 3, right: int = 3) -> pd.DataFrame:
    """Fractal swing highs/lows: a pivot high is a bar whose high exceeds the
    `left` bars before and `right` bars after it (confirmed `right` bars late,
    which is how it works in real time — no lookahead).

    Returns columns swing_high / swing_low holding the pivot price on the bar
    where the pivot is *confirmed*, NaN elsewhere.
    """
    h, l = df["high"], df["low"]
    win = left + right + 1
    ph = h.rolling(win, center=False).apply(
        lambda x: x[left] if x[left] == x.max() and (x[:left] < x[left]).all() and (x[left + 1:] < x[left]).all() else np.nan,
        raw=True)
    pl = l.rolling(win, center=False).apply(
        lambda x: x[left] if x[left] == x.min() and (x[:left] > x[left]).all() and (x[left + 1:] > x[left]).all() else np.nan,
        raw=True)
    return pd.DataFrame({"swing_high": ph, "swing_low": pl}, index=df.index)


def fair_value_gaps(df: pd.DataFrame, min_points: float = 2.0) -> pd.DataFrame:
    """Three-candle imbalances (ICT fair value gaps).

    Bullish FVG on bar i: low[i] > high[i-2] (gap between them).
    Bearish FVG on bar i: high[i] < low[i-2].
    Columns give the gap's top/bottom on the bar where it completes.
    """
    h2, l2 = df["high"].shift(2), df["low"].shift(2)
    bull = (df["low"] - h2) >= min_points
    bear = (l2 - df["high"]) >= min_points
    out = pd.DataFrame(index=df.index)
    out["fvg_bull_top"] = np.where(bull, df["low"], np.nan)
    out["fvg_bull_bot"] = np.where(bull, h2, np.nan)
    out["fvg_bear_top"] = np.where(bear, l2, np.nan)
    out["fvg_bear_bot"] = np.where(bear, df["high"], np.nan)
    return out


def enrich(df: pd.DataFrame, orb_minutes: int = 15) -> pd.DataFrame:
    """Attach every indicator the setup detectors need."""
    out = df.copy()
    out["ema9"] = ema(df["close"], 9)
    out["ema20"] = ema(df["close"], 20)
    out["atr"] = atr(df, 14)
    out["vwap"] = session_vwap(df)
    out = out.join(daily_levels(df))
    out = out.join(opening_range(df, orb_minutes))
    out = out.join(swing_pivots(df))
    out = out.join(fair_value_gaps(df))
    return out
