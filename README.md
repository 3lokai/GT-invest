# GT Invest

AI-assisted, rules-based swing trading research for **Indian cash equities**.

> **Status:** Early-stage research system. Read-only broker access only (Upstox market data, Groww portfolio view), no live trading and no validated profitability. Paper trading is the default. Latest status and open items: [docs/HANDOVER.md](docs/HANDOVER.md).

## Starting assumptions

- Existing portfolio: approximately **₹1 lakh in Groww**, available for strategy review (not automatically sold).
- New investment: **₹15,000–₹20,000 each month**.
- Intended execution broker: **Upstox** (pending authenticated integration).
- Time horizon: days to months; no intraday strategies, futures, options, margin or leverage.
- Instruments: liquid NSE mainboard shares, including qualifying small/microcaps; penny stocks are **not** exempt from liquidity/surveillance checks.
- Experience: explanations in ordinary English, not a wall of indicators.

## Workflow

1. Fetch official daily OHLCV data and corporate-action-adjusted history.
2. Screen momentum breakouts, trend templates and relative-strength rotation.
3. Apply market-wide filters, liquidity gates and strict portfolio risk budgets.
4. Produce a plain-English end-of-day briefing with **Buy / Watch / Exit / No action**.
5. Record proposed orders to a paper-trading journal; live orders require separate enablement and explicit per-order approval.
6. Evaluate results *after* brokerage, taxes, slippage, spread and failed fills.

## Scope and boundaries

- **Deterministic software** produces signals, position sizes, price levels, risk limits and orders.
- **Claude/OpenAI** explains candidates, summarizes company context, flags news/events and drafts a report. LLM output is untrusted and cannot override risk rules.
- **No autonomous orders** by default. No hardcoded credentials. No synthetic-demo results presented as investment performance.
- Holdings imported from Groww must retain their cost basis; an Upstox account cannot sell shares held with Groww unless transferred.

## Run the local demonstration

Requires Python 3.11+:

```bash
python -m pip install -e .
python -m gt_invest --demo
python -m unittest discover -s tests -v
```

The demonstration uses **fabricated price data** and does not connect to any broker. It is not a backtest or trade recommendation.

To scan real NSE mainboard (`EQ` series) stocks, put your read-only Upstox Analytics Token in `.env` (see `.env.example`), then:

```bash
python -m gt_invest --scan                     # latest session Upstox has published
python -m gt_invest --scan --as-of 2026-10-30  # an earlier day
python -m gt_invest --scan --source nse        # raw NSE bhavcopy files instead, no token needed
```

Upstox candles are adjusted for splits and bonuses. A fresh run makes one request per stock (~2,750), and Upstox allows 2,000 requests per 30 minutes, so it takes about 30 minutes. Re-runs within 2 hours reuse the cache in `data/raw/upstox/` (git-ignored). The output always prints which session it scanned. When Upstox publishes each session's candles is still being measured (`--latest`).

To label the trend of specific stocks, for example your holdings (typed at runtime, never stored):

```bash
python -m gt_invest --trend HDFCBANK SBIN   # uptrend / weakening / downtrend; a chart description, not a sell signal
```

With `--source nse`, the first run downloads about 220 daily files (~40 MB, ~3 min) into `data/raw/bhavcopy/`. Those prices are **not** adjusted for splits or bonuses.

Either way, a stock's history is cut at any overnight gap over 25% or any session it was missing from `EQ`, so relisted or surveillance-moved stocks (and, on NSE data, recently split ones) are skipped. Output is research candidates only.

To backtest the breakout scanner on every NSE file since July 2024 (about 590 files, ~5 min on the first run):

```bash
python -m gt_invest --backtest   # writes reports/backtest-breakout-v1-<last session>.md
```

It replays the scanner day by day, including stocks that were later delisted. Fills happen at the next session's open with slippage, and Upstox delivery charges apply. Each month adds a ₹20k deposit, and the result is compared with the Nifty 500 bought with the same deposits. The data covers only about 18 months of trading after the warm-up: one market regime, not proof of anything.

## Next milestones

See [Product brief](docs/PRODUCT.md), [Architecture](docs/ARCHITECTURE.md), [Safety gates](docs/SAFETY.md) and [Strategy playbook](docs/STRATEGY.md). Implementation tasks are in GitHub issues.
