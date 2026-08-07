# TradingView Scripts

Pine Script indicators I'm using on TradingView, saved here for version control.

## Liquidity Sweeps [LuxAlgo]

File: [`liquidity-sweeps-luxalgo.pine`](liquidity-sweeps-luxalgo.pine)

Original author: [LuxAlgo](https://www.tradingview.com/u/LuxAlgo/) — licensed under
[CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/) (attribution required, non-commercial use only, share-alike).
Script page: https://www.tradingview.com/script/JRqryeJ5-Liquidity-Sweeps-LuxAlgo/

This is an **indicator** (chart overlay), not a strategy — it draws levels and zones but does not
place backtested entries/exits.

### Overview

The Liquidity Sweeps indicator detects the presence of liquidity sweeps on the chart, while also
providing potential areas of support/resistance or entry when liquidity levels are taken. In the
event of a Liquidity Sweep, a **Sweep Area** is created which may provide further areas of interest.

### Usage

A Liquidity Sweep occurs when the price breaks through a liquidity level (LqL), after which the
price returns below/above the liquidity level, forming a wick. The script detects two ways this
can happen:

1. **Wick sweep** — a wick passes an LqL after which the price quickly returns.
   Shown with a **dotted** line.
2. **Outbreak & retest** — first the closing price breaks through an LqL; after a while, the
   price retests the LqL and forms a wick in the opposite direction.
   Shown with a **dashed** line.

When a Liquidity Sweep takes place, the "wick-to-LqL" distance is highlighted. A small 3-bar-long
dotted line starts from the opposite end of the wick as an extra aid to determine potential
support/resistance/entry levels.

Green markings are bullish sweeps (of swing lows); red markings are bearish sweeps (of swing
highs). Colors can be changed in the settings.

### Sweep Areas

The distance between the LqL and the maximum limit of the wick forms a **Sweep Area**, which can
act as a potential support/resistance or entry zone.

- The trigger bar is where the high/low crossed an LqL; a box starts between the LqL and that
  wick's extreme.
- The opposite end of the trigger bar's wick is the starting point of the short dotted line —
  price touching the Sweep Area and returning, or breaking that small dotted line, can present
  entry opportunities.
- When the Sweep Area is mitigated (price closes through the far side of the box) or a set number
  of bars has passed (`Max bars`), the box stops updating.

### Settings

**Liquidity Sweeps**

- **Swings**: Period used for the swing detection; higher values return longer-term liquidity
  levels (default 5).
- **Options**:
  - *Only Wicks* — only detects a sweep when a wick sweeps a previous wick.
  - *Only Outbreaks & Retest* — only detects a sweep when price breaks an LqL, returns, retests
    it, and forms a wick in the opposite direction.
  - *Wicks + Outbreaks & Retest* — both.
- Bull/Bear colors for the sweep lines.

**Sweep Area**

- **Extend**: Enables/disables extension of the Sweep Area boxes to the right.
- **Max bars**: Limits the extension to a set number of bars (default 300).
- Bull/Bear colors for the Sweep Area boxes.

### How to load it on TradingView

1. Open a chart → Pine Editor → paste the script → "Add to chart".
2. Works on any symbol/timeframe.

## Liquidity Sweeps + Signals (modified version)

File: [`liquidity-sweeps-signals.pine`](liquidity-sweeps-signals.pine)

A modified copy of the script above (same CC BY-NC-SA 4.0 license, LuxAlgo attribution kept)
that turns detections into explicit trade suggestions:

- **▲ green triangle below a bar** — bullish liquidity sweep confirmed on that bar's close
  (a swing low was taken and price closed back above it)
- **▼ red triangle above a bar** — bearish liquidity sweep confirmed
- **◆ small diamond** — price retested a still-active sweep area and closed back outside it
  (a "second chance" entry; requires `Extend` to be on)

Each of the four events has a matching `alertcondition`, so alerts can be created in
TradingView: Alert → Condition → *Liquidity Sweeps + Signals* → pick the event → set trigger
to **Once Per Bar Close**.

The markers are suggestions, not a backtested strategy — entry/stop/exit rules are documented
in the playbook. Signals evaluate on closed bars and do not repaint.
