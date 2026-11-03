# GT Invest

AI-assisted, rules-based swing trading research for **Indian cash equities**.

> **Status:** Early-stage research system. No broker credentials, no live trading and no validated profitability. Paper trading is the default.

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

## Next milestones

See [Product brief](docs/PRODUCT.md), [Architecture](docs/ARCHITECTURE.md) and [Safety gates](docs/SAFETY.md). Implementation tasks are in GitHub issues.
