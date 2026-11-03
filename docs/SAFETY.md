# Safety and validation rules

## Unconditional controls
1. Paper is the only supported mode at project bootstrap.
2. Any future live trading requires a separate authenticated broker write adapter, explicit enablement and per-order human approval; no auto-execution without a new explicit decision.
3. No leverage, intraday product types, futures/options, naked shorts or margin.
4. No LLM, downloaded webpage or social message is trusted as an order request.
5. No order placement, modification, transfer or cancellation can be triggered by this repo today.
6. Broker access for agents is read-only: the Upstox Analytics Token cannot trade, and Groww MCP tools are limited by the allow/deny lists in `.claude/settings.json`. Re-check the Groww tool list whenever Groww updates its server; new tools are neither allowed nor denied by default.
7. Keep Groww DDPI (demat debit authorisation) off, so no connected tool can sell holdings.

## Research defaults — subject to testing
- Initial maximum planned stop risk: 0.5% of total account equity per candidate.
- Initial notional limit per proposed new position: 10% of total account equity.
- Initial speculative microcap sleeve: <=10% of portfolio **in aggregate**, only for securities with verified liquidity and permitted trading status.
- Reject candidates lacking enough history, daily volume, reliable pricing, or consistent security identifiers.
- Do not infer risk from share price; ₹5 per share is not a risk metric.
- Hard-stop lower-circuit, ASM/GSM/ESM or SME-lot constraints require specific handling; default exclusion until implemented.
- Paper systems must model failed exits and slippage. Stops are not guaranteed exit prices.
- Portfolio-level aggregate exposure, daily drawdown kill switches, same-industry concentration and correlated gap losses are mandatory prior to live release.

## Required gates before live
- [ ] Licensed/official data source and full instrument master.
- [ ] Reproducible historical walk-forward tests and benchmark comparison after all costs.
- [ ] At least a meaningful paper evaluation with simulated gaps, slippage and rejected orders.
- [ ] Broker sandbox/test or safe dry run where possible.
- [ ] Approved risk limits and emergency stop mechanism.
- [ ] Authentication, static IP and session-expiry handling validated against current Upstox docs.
- [ ] Explicit account-funding and live-trading authorization.
- [ ] Immutable order/event journal; retry/idempotency/reconciliation tests.
- [ ] Confirmed regulatory and applicable brokerage requirements.
