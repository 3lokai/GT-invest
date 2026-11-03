# GT Invest — Strategy Playbook (Research v0.1)

> **Status:** Research hypotheses, not validated trading advice, an approved allocation, or guaranteed performance. Written to preserve the decisions from the original planning discussion. No live execution is authorized by this document.
>
> **Companion docs:** [Product](PRODUCT.md) · [Architecture](ARCHITECTURE.md) · [Safety](SAFETY.md).

## 1. Investor mandate and operating style

- Starting account: **approximately ₹1,00,000 of existing equity holdings with Groww**, not necessarily free cash. The system should assess these holdings and propose retain/exit decisions, not forcibly liquidate them.
- New capital: **₹15,000–₹20,000 contributed monthly**, building a larger account over time. Cash may wait for a valid setup; a contribution is not a required monthly trading volume trading volume.
- Style: **aggressive, rules-based swing/position trading**, holding **days to months**, with a long-only cash equity portfolio. Not day trading; no derivatives, margin, leverage, F&O or short sales.
- Workflow: **one EOD screening/review window and one optional next-morning execution window**. These are maximum interaction windows, not required trades.
- User experience: do the numerical work automatically, show short **BUY / WATCH / EXIT / NO ACTION** suggestions with an explanation and plain-language downside. Human approval is required for actual orders.
- Execution broker under consideration: Upstox. Groww holds the initial portfolio. Research and import do **not** imply a transfer or sale.

## 2. Strategies discussed — candidate systems, not a single magic algorithm

| Candidate | Intellectual origin | Entry idea | Typical hold (illustrative) | Why test it | Principal failure mode |
|---|---|---|---|---|---|
| **Qullamaggie-style breakout** | Kristjan Kullamägi | Strong prior run, orderly consolidation, fresh breakout with demand/volume | Weeks to months | Aggressive leadership-stock momentum, including liquid smaller caps | False breakouts and sharp reversals |
| **Minervini SEPA / VCP-inspired** | Mark Minervini | Strong long-term uptrend and progressively tightening price contraction before breakout | Weeks to months | More selective entries; defined setup structure | VCP pattern recognition can become subjective/overfit |
| **Darvas box** | Nicolas Darvas | Break over a well-defined price box, with a box-related exit | Weeks | Simple, reproducible rules for EOD automation | Whipsaw in sideways markets |
| **CAN SLIM-inspired growth/momentum** | William O'Neil | Earnings/sales leadership plus favorable price action and breakout | Weeks to months | Fundamental quality layer to filter weak businesses | Financial reporting lag, data gaps, valuation sensitivity |
| **Cross-sectional relative-strength rotation** | Established momentum factor research | Rank liquid stocks by ~3/6/12-month strength, hold top ranks, periodic rebalance | Months | Highly objective baseline and complement to chart setups | Crash/reversal risk and high turnover |

**Original shortlist for direct comparison:** Qullamaggie-inspired breakout, Minervini-inspired VCP, and three/six-month relative-strength rotation. Darvas and CAN SLIM remain useful optional benchmarks/extensions.

These are **inspired-by systematic variants**, not claims to replicate discretionary traders' proprietary decision-making. Every signal must be fully defined before a backtest.

### Intended experiment: aggressive hybrid

A **70% breakout / 20% relative-strength / 10% speculative microcap** split was discussed as an *illustrative research budget* at ₹20k/month: ₹14k / ₹4k / ₹2k. This is **not** a mandatory purchase schedule, performance-tested allocation, or instruction to place subeconomic ₹2k microcap orders. Actual buying depends on cash, present positions, risk and trading costs.

Initial risk defaults proposed separately:
- Max planned stop loss per new trade: **0.5% of total account equity**; this is *planned* loss only, not worst-case loss.
- Max new position notional: **10% of account equity**.
- Microcap exposure: **<=10% of total portfolio, aggregate**.
- No forced investment when a setup is absent; default outcome may be **NO ACTION**.
- No live trading until full portfolio exposure controls, slippage modelling, and approval/reconciliation gates exist.

These defaults are **starting constraints to validate**, not a substitute for a portfolio-level risk engine. Exposure inherited from Groww holdings must be included when computing limits.

## 3. First reproducible setup: price/volume breakout (V1 hypothesis)

**Universe / eligibility before ranking**
1. NSE **mainboard cash equities**, starting with EQ; not SME lots, trade-for-trade, or securities with problematic surveillance/trading restrictions. Point-in-time instrument lists matter.
2. Require a verified minimum liquidity screen; working hypothesis **20-session average traded value >₹3 crore** (the scanner currently approximates this as close × volume over the 20 sessions before the signal day, not NSE's reported traded value), plus a spread/market-impact gate and minimum valid history. Be particularly conservative for penny stocks.
3. Exclude or separately control recent splits/bonuses, suspensions, extreme illiquidity, untrusted corporate-action data, and applicable ASM/GSM/ESM or circuit restrictions.
4. Optional market regime filter for *new entries*: **Nifty 50 close above its 200-session moving average**. This was discussed but is **not yet coded in the bootstrap scanner**. Backtest its usefulness rather than treating it as canonical.

**Research entry rules discussed**
1. Price has already advanced about **30% over roughly 3 months (63 trading sessions)**.
2. Recent **10–40 session consolidation**, ideally narrowing volatility; this is a conceptual requirement **not yet modeled** by the first scanner.
3. Stock price is above the **50- and 200-session moving averages**, with favorable trend alignment.
4. Completed daily candle closes above the **prior 20-session high**.
5. Breakout day's volume is **>=1.5×** the average volume of the preceding 20 sessions.
6. Check that the next morning's price is still within a reasonable, predeclared distance from the planned entry; **never** assume an EOD signal fills at that day's closing price.

**Important implementation distinction:** the current `strategy.scan_breakout` is a **minimal technical breakout hypothesis**: 20-day high + volume + 63-day momentum + SMA alignment + turnover. It does **not** detect true VCP/consolidation, use a market-regime filter, check surveillance lists, or validate the actual next-session entry. Do not label it a full Qullamaggie or Minervini implementation. By default it runs on Upstox daily candles, which are split/bonus adjusted. `bhavcopy.histories()` still keeps only each symbol's trailing run of consecutive `EQ` sessions with no overnight gap over 25%, as a sanity check (and as the only split protection on raw NSE files via `--source nse`).

**Research exits**
- Initial indicative stop from market structure/volatility; **6–8%** was discussed as a starting range. The bootstrap's fixed **7% below signal close** is only an approximation, **not** a live protective order.
- Backtest a trailing exit (e.g. volatility-adjusted or moving-average based) and a time-stop for stalled breakouts, alongside the initial stop.
- A stock may gap through a stop, enter a lower circuit, or be illiquid. Simulated exits must be modelled as *failed or worse fills* where relevant. Never claim the stop caps actual loss.
- Explicitly distinguish a position's **research signal** from its **approval** and **broker order**.

## 4. Penny stocks: permitted selectively, never simply because the share price is low

The user's openness to penny stocks means **willingness to consider high volatility**, *not* an instruction to seek the lowest-priced tickers.

- Assess market capitalization, real traded turnover, spreads, order-book depth, ownership/pledges, disclosures and corporate actions. A ₹5 stock can be more dangerous and more expensive to trade than a ₹500 stock.
- Price circuits and surveillance/settlement restrictions can make a position impossible to exit when desired.
- Exclude low-liquidity microcaps by default. Do not loosen liquidity rules solely to fill the speculative allocation.
- Consider the SME market only as a separately researched future product: lot sizes and trading mechanics can be incompatible with the account's current size.
- Compare a **no-penny-stock portfolio** against any microcap addition after costs and actual exit assumptions. The sleeve is optional, not a target.

## 5. Backtesting protocol — judge the strategy, not the story

Evaluate each strategy over multiple market regimes with historical, point-in-time data; avoid survivor-only stock lists and look-ahead bias. Record:
- Data provenance, corporate-action adjustment method, constituent changes/delistings, suspensions and missing candles.
- Next-eligible-session entries, tradeable limit prices, realistic gaps, spreads, slippage and volume participation.
- Indian trading costs: brokerage, STT, exchange/SEBI fees, GST where applicable, stamp duty, DP charges, and a separately documented **tax estimate** (holding period matters); use current rules when running a real test.
- Capital contributions every month, cash drag, portfolio funding, position concentration and actual share counts.
- CAGR/total and time-weighted returns, max drawdown, worst losing streak, win rate, average win/loss, turnover and costs.
- Comparison with a **Nifty 500 / suitable total-return benchmark** and a buy-and-hold alternative, with **matched cash contributions**.
- Walk-forward/out-of-sample tests and robustness to parameter changes. A great in-sample equity curve does not justify live orders.

**Reject a strategy** if it relies on impossible fills, thin liquidity, unfunded purchases, hindsight universe selection, or LLM discretionary overrides. Positive simulated returns do not guarantee future profits.

## 6. Operational acceptance criteria

**Research mode now:** daily report includes what qualified, what failed, why, hypothetical position size, planned downside and “paper only” flag. Store raw signal and exact strategy version.

**Before paper portfolio is considered credible:** independent fills and portfolio ledger; current positions and cash; fees/slippage/circuit handling; market-regime testing; monthly capital additions; risk limits at portfolio level.

**Before optional live mode:** explicit user authorization, funded order-capable Upstox account, genuine current instrument permissions, strict independent pretrade limits, broker-session/auth safeguards, human confirmation of every order, idempotency, order reconciliation and kill switch. A direct Claude/broker trade tool must never bypass these controls.

## 7. Decisions not yet made

1. Which of the three core strategies wins after cost and walk-forward comparison.
2. Whether the Nifty 50 regime filter helps or excessively delays entries.
3. Whether to allow any microcap allocation after modeling failed exits; if so, precise minimum turnover and spread threshold.
4. How to liquidate or transfer existing Groww positions, **only after** comparing taxes, liquidity, current portfolio signals and account restrictions.
5. Whether 70/20/10 strategy allocation should change as the account grows.

**Principle:** automate data gathering, math, candidate discovery and explanations immediately; keep investment decisions auditable and broker orders permissioned.
