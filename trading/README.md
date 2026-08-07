# TradingView Scripts

Pine Script indicators I'm using on TradingView, saved here for version control.

## Liquidity Sweeps [LuxAlgo]

File: [`liquidity-sweeps-luxalgo.pine`](liquidity-sweeps-luxalgo.pine)

Original author: [LuxAlgo](https://www.tradingview.com/u/LuxAlgo/) — licensed under
[CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/) (attribution required, non-commercial use only, share-alike).

### What it does

This is an **indicator** (chart overlay), not a strategy — it draws levels and zones but does not
place backtested entries/exits.

- Detects swing highs and swing lows using `ta.pivothigh` / `ta.pivotlow` with a configurable
  `Swings` length (default 5 bars on each side).
- Watches those swing levels for **liquidity sweeps**, in two forms:
  - **Wick sweep:** price wicks through the level intrabar but closes back on the original side
    (e.g. high pierces a swing high while the close stays below it). Shown with a dotted line
    and a shaded sweep zone.
  - **Outbreak & retest:** price closes through the level (a real break), then later trades back
    through it and closes on the original side again. Shown with a dashed line and a sweep zone.
- The `options` input selects which of the two detection modes are active
  (`Only Wicks`, `Only Outbreaks & Retest`, or both).
- **Sweep Area** settings control the shaded zones: they extend to the right (up to `Max bars`,
  default 300) until price closes through the far side of the zone, which marks the zone as broken.
- Levels are cleaned up automatically once they are mitigated/taken or after 2000 bars.

### How to use it on TradingView

1. Open a chart → Pine Editor → paste the script → "Add to chart".
2. It works on any symbol/timeframe; green markings are bullish sweeps (of swing lows),
   red markings are bearish sweeps (of swing highs).
