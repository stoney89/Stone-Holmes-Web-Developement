"""Data loading for the MNQ toolkit.

Three sources, in order of preference:
1. TradingView CSV export (best — it's the exact data you chart on)
2. yfinance NQ=F intraday bars (free, limited history: ~60 days of 5m, ~7 days of 1m)
3. Synthetic data (for smoke-testing the pipeline only — never draw conclusions from it)

All loaders return a DataFrame indexed by tz-aware US/Eastern timestamps with
columns: open, high, low, close, volume.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

EASTERN = "America/New_York"
REQUIRED_COLS = ["open", "high", "low", "close", "volume"]


def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    df = df.rename(columns={c: c.strip().lower() for c in df.columns})
    aliases = {"vol": "volume", "volume ma": None, "time": None, "date": None}
    for src, dst in aliases.items():
        if src in df.columns and dst is None:
            df = df.drop(columns=[src])
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if "volume" in missing:
        df["volume"] = 0
        missing.remove("volume")
    if missing:
        raise ValueError(f"Data is missing columns: {missing}")
    df = df[REQUIRED_COLS].astype(float)
    # Databento raw exports scale prices by 1e9 (fixed-point ints); undo that.
    if df["close"].median() > 1e6:
        for col in ("open", "high", "low", "close"):
            df[col] = df[col] / 1e9
    df = df[~df.index.duplicated(keep="first")].sort_index()
    return df


def load_csv(path: str) -> pd.DataFrame:
    """Load an OHLCV CSV from TradingView, Databento, or any similar export.

    Handles TradingView ('time' as ISO-8601 or unix seconds) and Databento
    ('ts_event' in nanoseconds), auto-detecting the epoch unit by magnitude.
    """
    df = pd.read_csv(path)
    candidates = ("time", "date", "datetime", "timestamp", "ts_event", "ts_recv")
    time_col = next((c for c in df.columns if c.strip().lower() in candidates), None)
    if time_col is None:
        raise ValueError("No time/date column found in CSV")
    ts = df[time_col]
    if pd.api.types.is_numeric_dtype(ts):
        mag = float(ts.abs().max())
        unit = "s" if mag < 1e11 else "ms" if mag < 1e14 else "us" if mag < 1e17 else "ns"
        idx = pd.to_datetime(ts, unit=unit, utc=True)
    else:
        idx = pd.to_datetime(ts, utc=True, format="mixed")
    df.index = idx.dt.tz_convert(EASTERN)
    return _normalize(df.drop(columns=[time_col]))


# Backwards-compatible alias — load_csv handles TradingView exports and more.
load_tradingview_csv = load_csv


def load_yfinance(symbol: str = "NQ=F", interval: str = "5m", period: str = "60d") -> pd.DataFrame:
    """Fetch intraday futures bars from Yahoo Finance. Requires `pip install yfinance`."""
    import yfinance as yf

    raw = yf.download(symbol, interval=interval, period=period, progress=False, auto_adjust=False)
    if raw is None or raw.empty:
        raise RuntimeError(f"yfinance returned no data for {symbol}")
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)
    raw.index = raw.index.tz_convert(EASTERN)
    return _normalize(raw)


def synthetic_mnq(days: int = 30, seed: int = 7, freq: str = "5min", start_price: float = 21000.0) -> pd.DataFrame:
    """Generate plausible-looking NQ bars for pipeline smoke tests.

    Random-walk with a U-shaped intraday volatility profile and occasional
    trend days. This exists so the code can be exercised without market data;
    backtest numbers on it are meaningless.
    """
    rng = np.random.default_rng(seed)
    sessions = pd.bdate_range(end=pd.Timestamp.now(tz=EASTERN).normalize(), periods=days)
    frames = []
    price = start_price
    for day in sessions:
        idx = pd.date_range(day + pd.Timedelta(hours=9, minutes=30),
                            day + pd.Timedelta(hours=15, minutes=55),
                            freq=freq, tz=EASTERN)
        n = len(idx)
        # U-shaped vol: hot open, quiet lunch, active close
        t = np.linspace(0, 1, n)
        vol = 6.0 * (1.6 - 2.2 * t * (1 - t) * 4 / 1.6) ** 0.5
        vol = np.clip(vol, 2.5, 12.0)
        drift = rng.normal(0, 1.2) * np.ones(n) / n * 60  # occasional trend day
        moves = rng.normal(0, 1, n) * vol + drift
        closes = price + np.cumsum(moves)
        opens = np.concatenate([[price], closes[:-1]])
        spread = np.abs(rng.normal(0, 1, n)) * vol * 0.8 + 1.0
        highs = np.maximum(opens, closes) + spread * rng.uniform(0.2, 1.0, n)
        lows = np.minimum(opens, closes) - spread * rng.uniform(0.2, 1.0, n)
        volume = (rng.uniform(500, 1500, n) * vol / vol.mean()).astype(int)
        frames.append(pd.DataFrame(
            {"open": opens, "high": highs, "low": lows, "close": closes, "volume": volume},
            index=idx))
        price = closes[-1] + rng.normal(0, 15)  # overnight gap
    df = pd.concat(frames)
    return df.round(2)


def rth_only(df: pd.DataFrame) -> pd.DataFrame:
    """Filter to regular trading hours, 9:30-16:00 ET."""
    return df.between_time("09:30", "15:59")
