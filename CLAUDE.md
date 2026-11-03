# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

@AGENTS.md

This is paper-only research for Indian NSE cash equities. No broker is connected, and nothing in this repo may place, modify or cancel orders. Before changing signals, sizing or anything execution-shaped, read `docs/SAFETY.md`, which lists the risk defaults and the gates required before live trading.

## Commands

Python 3.11+, stdlib only (no runtime deps, no linter configured).

```bash
python -m pip install -e .                                   # install (src/ layout)
python -m unittest discover -s tests -v                      # all tests
python -m unittest tests.test_risk.TestPositionSizing.test_cash_budget_limited  # single test
python -m gt_invest --demo                                   # synthetic smoke test (CI runs this too)
python -m gt_invest --scan [--as-of YYYY-MM-DD]             # real NSE scan; downloads/caches to data/raw/bhavcopy/
```

CI (`.github/workflows/ci.yml`) runs exactly the install, unittest and `--demo` steps above.

## Architecture

Pipeline (see `docs/ARCHITECTURE.md` for the full future flow): candles → `strategy.scan_breakout` → `BreakoutSignal` → `risk.size_position` → `PositionProposal`. A signal is not an order, and a proposal is not an order either.

- `strategy.py`: a pure function over one symbol's chronological daily candles. Any bad input (too little history, duplicate or unsorted sessions, mixed symbols, invalid OHLC) returns `None` rather than raising, so a rejected candidate and a malformed input look the same to the caller. Thresholds live in the frozen `BreakoutConfig`.
- `risk.py`: works only in `Decimal`. It raises `ValueError` for non-Decimal or non-finite inputs and returns `None` when no whole share fits. Quantity is the smaller of two limits: the risk budget (`max_loss_fraction_of_equity` divided by per-share risk) and the notional budget (`min(cash, equity × max_notional_fraction)`).
- `bhavcopy.py`: the only real data source. Network access lives only in `fetch()`, and tests stay offline by using in-memory zips. A 404 means NSE has no file for that day (holiday, or not published yet), so it is never cached. NSE does not adjust for splits or bonuses, so `histories()` keeps only each symbol's trailing run of consecutive `EQ` sessions with no overnight gap over 25%. Replace that cut with real corporate-action adjustment once that data exists.
- Float/Decimal boundary: `models.py` stores prices as `float`; money is converted with `Decimal(str(x))` before sizing (see `__main__.py`). Keep any arithmetic that sets an executable quantity or price in `Decimal`.
- `__main__.example_candles()` is the fabricated dataset shared by the demo and `tests/test_strategy.py`. Changing it changes the test expectations. Never present its output as market data or performance.
- The scanner emits signals on the closing price. Backtests must fill at a later session and include costs and slippage, not at `reference_close`.

Broker access is read-only and configured outside the code. The Upstox Analytics Token lives in `.env` (see `.env.example`). The Groww MCP permissions live in `.claude/settings.json`: read tools are allowed and likely order tools are denied. Don't loosen them. The table in `docs/ARCHITECTURE.md` explains why each access route was chosen. Current status and open issues are in `docs/HANDOVER.md`.

Planned modules (corporate actions, `backtest/`, `brokers/upstox/`, `journal/`, `reports/`) don't exist yet. Milestones M1–M5 are in `docs/PRODUCT.md`.
