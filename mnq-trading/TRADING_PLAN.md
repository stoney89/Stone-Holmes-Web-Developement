# MNQ Trading Plan

This is the written plan the code in this folder enforces. Print it. Every rule
here exists because breaking it is how traders blow up.

---

## 0. Honest ground rules (read first)

- **Most day traders lose money.** Independent studies of retail futures/CFD
  traders consistently find 70–90% are net losers over a year. The edge that
  separates the rest is not a secret setup — it's risk control, selectivity,
  and a feedback loop (journal + review). That's what this toolkit builds.
- **"$500–1,000/week" is a goal, not a starting point.** At a professional-level
  10–20% monthly return (which is *very* good), $1,000/week implies roughly a
  $25k–$50k account or a funded prop account. Do not size up to force the
  number out of a small account — that's how small accounts die.
- **The sequence is fixed:** paper trade → prove the numbers → tiny live size
  (1 MNQ) → scale only after the numbers hold. No skipping stages because a
  week went well.

## 1. The three setups (and only these three)

Trade nothing that isn't one of these. All are implemented in `setups.py` so
they can be backtested and so "did I follow the rules?" has an objective answer.

### A. Opening Range Breakout (ORB) — the anchor setup
- Mark the 9:30–9:45 ET range. No trades before 9:45.
- Long: a 5m bar **closes** above the range high by 2+ points. Short: mirror.
- Stop: range midpoint. Target: 2R minimum, trail runners past 2R if trending.
- One breakout per direction per day, entries 9:45–11:30 only.
- **Why first:** it's fully mechanical — no judgment calls — so it's the best
  setup for building discipline and getting clean backtest data.

### B. VWAP trend continuation
- Regime: price above VWAP **and** 9EMA > 20EMA → longs only (mirror for shorts).
- Trigger: pullback into 20EMA/VWAP, then a close back above the 9EMA.
- Stop: below the pullback low − 0.5×ATR. Target: 2R or the next liquidity level.
- No entries 11:30–13:30 (lunch chop) or after 15:00.

### C. Liquidity sweep → CHoCH (the "A+" reversal)
- Price sweeps PDH/PDL or the overnight high/low, then breaks the most recent
  swing in the opposite direction (change of character) within ~1 hour.
- Enter the CHoCH break (or the retrace into the FVG it leaves — better price,
  fewer fills). Stop beyond the sweep extreme. Target: 2R+ / opposing liquidity.
- This is the highest-quality, lowest-frequency setup. It is a *bonus*, not
  the bread and butter, until your journal proves you execute it well.

## 2. Risk rules (non-negotiable)

| Rule | Value |
|---|---|
| Risk per trade | ≤ 1% of account (paper: pretend $5,000 → $50/trade) |
| Minimum reward:risk | 2:1 to a real level, or no trade |
| Max trades per day | 4 |
| Daily stop | 2 consecutive losses OR −2R on the day → done, walk away |
| Weekly stop | −6R on the week → flat until Monday, review journal |
| Stops | Set at entry, at structure. Never widened. Ever. |
| News | Flat 15 min before/after CPI, FOMC, NFP (check ForexFactory red folders) |
| Grade gate | Only A/A+ trades at full size (run `scorer.py` before every entry) |

MNQ math you must know cold: **$2 per point, $0.50 per tick (0.25).** A 30-point
stop = $60 risk per contract, so a $50 risk budget means that trade is a pass —
you don't "make it fit" by widening mental math.

## 3. Paper trading phase — the graduation gates

Paper trade on TradingView (Paper Trading connection) or a broker sim, taking
**every** valid A/A+ setup, journaling every trade in `journal_template.csv`
(including skipped C setups). You graduate to live only when ALL of these hold:

1. **≥ 60 trades** logged (statistical minimum — 20 trades tells you nothing).
2. **≥ 8 weeks** of trading (covers different market regimes).
3. **Positive expectancy**: average ≥ +0.3R per trade after simulated costs.
4. **Rule adherence ≥ 90%** ("followed_plan = yes" in the journal).
5. **Max drawdown in the sim ≤ 10R.**

If any gate fails, you don't lower the gate — you diagnose with `journal.py`
(which setup/session is bleeding?) and run another 4-week block.

Then go live with **1 MNQ contract only** for at least a month. Live fills,
slippage, and your own adrenaline are worse than sim; expect performance to
drop ~20–30% at first. Scale to 2 contracts only after a profitable month at
1, and so on — add one contract per profitable month, remove one after any
losing week.

## 4. The financial route (beginner → full time)

**Step 0 — before any trading dollars:** 3–6 months of living expenses saved,
no high-interest debt, and trading capital you can lose 100% of without it
changing your life. Trading income is irregular for years; full-time is a
distant milestone, not a 6-month plan.

**Option A — self-funded (recommended to start):**
- Open a futures account at a discount futures broker (AMP, NinjaTrader,
  Tradovate/TradingView-integrated, Optimus). Tradovate connects natively to
  TradingView, which fits your stack.
- $2,000–5,000 is enough to trade 1 MNQ responsibly ($50/trade risk = 1–2.5%).
- All P&L is yours; futures get favorable 60/40 tax treatment in the US
  (Section 1256 — talk to a tax person when you're profitable).

**Option B — prop firm evaluations (Topstep, Apex, etc.):**
- Cheap access to size ($150–350/month per eval) and their drawdown rules
  force discipline, which is genuinely useful.
- But: most people fail evals repeatedly and the subscription fees are the
  firms' real business model. Treat an eval as a *graduation reward* for
  passing the paper gates above — never as a substitute for them, and never
  run more than one at a time.
- Realistic bridge to your goal: a funded 50k account risking 0.5–1% per trade
  with a proven +0.3R/trade edge and ~15 trades/week is in the
  $500–1,000/week zone. That's the credible path to the number you named.

**Do not:** trade options on margin "to grow faster", revenge-trade evals,
fund an account with credit, or quit a job for trading before 12+ consecutive
profitable months.

## 5. Daily routine

**Pre-market (9:00–9:25):** mark PDH/PDL, ONH/ONL on TradingView; note the 15m
trend; check the news calendar; write ONE sentence: today's bias and the level
you'll trade against.

**Session (9:45–11:30, optionally 14:00–15:30):** wait for a setup from the
list, run the `scorer.py` checklist, execute, manage per plan. No setup = no
trade; a flat day following the plan is a *winning* day.

**Post-market (10 min):** journal every trade + screenshot; tag mistakes;
Friday: run `python3 journal.py my_journal.csv` and read what it says.

## 6. Roadmap for this repo

- [x] Setup detection, backtester with real MNQ costs, scorer, journal analyzer
- [ ] Backtest on real data (TradingView 1m/5m export — best; yfinance for quick checks)
- [ ] Walk-forward split: tune nothing, verify each setup's edge holds out-of-sample
- [ ] TradingView Pine Script alerts mirroring `setups.py` (so charts ping you in real time)
- [ ] Auto-journal: import broker/sim fills, auto-grade against the plan
- [ ] Only after months of live consistency: semi-automation via Tradovate API
      (alerts → one-click order tickets first; full automation last, if ever)
