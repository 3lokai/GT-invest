# Product brief — GT Invest

## Goal
An automated personal research and swing-trading assistant that proposes cash-equity trades for a non-finance user who prefers plain-English decisions. It must be capable of running on a server from day one, but must not place real orders until validation and explicit approval.

## Starting position
- Approx ₹1 lakh invested at Groww; review all existing holdings, but do not automatically liquidate them.
- ₹15k–₹20k of additional capital monthly; do not assume the entire contribution needs immediate deployment.
- Upstox account available but initially unfunded; possible destination for eventual execution.
- Decision cadence: after market close for analysis, one optional morning order check. No intraday trading.

## Strategy candidates (hypotheses, not proven profits)
1. Qullamaggie-style price/volume consolidation breakout.
2. Minervini trend template + VCP-inspired setup.
3. Three/six-month cross-sectional relative-strength rotation.

First code implementation is a deliberately simplified **end-of-day breakout scanner**. It is not an implementation of the full discretionary Qullamaggie or Minervini systems.

## UX
Daily notification should say:
- Action: BUY / WATCH / EXIT / NO ACTION.
- Why it qualified, in 2–3 simple sentences.
- Proposed rupee allocation and maximum planned loss at stop.
- Events/restrictions that could invalidate the suggestion.
- Whether it is simulation or an actual request for approval.

## Milestones
**M0 — Repo foundation:** Paper-only strategy, risk sizing, docs and test suite.
**M1 — Market data:** Authenticated Upstox read-only market data, instrument master, corporate-action handling, daily scheduler.
**M2 — Research:** Three comparable strategies, walk-forward historical testing with transaction costs, liquidity, taxes and delisted constituents.
**M3 — Portfolio:** Import Groww holdings, preserve tax lots, map securities, audit portfolio and funding.
**M4 — Journal + briefing:** Paper fills, performance and drawdown tracking, plain-English LLM commentary with citations, Telegram delivery.
**M5 — Optional live:** Explicitly funded Upstox account, registered IP where required, human-confirmed orders, risk guardrails, idempotent reconciliation, kill switch.

## Success criteria
- Zero broker write actions in paper mode.
- Each strategy can be replayed deterministically and independently tested.
- Walk-forward testing reports return, max drawdown, turnover, worst gaps, win/loss statistics and after-cost vs benchmark results.
- All executed orders are traceable to a versioned signal, strategy, risk check and explicit approval.
- One-click disable/kill switch that prevents new orders.

## Non-goals
Day trading, derivatives, leverage, blind trust in LLM picks, illiquid lower-circuit gambling, guaranteed returns.
