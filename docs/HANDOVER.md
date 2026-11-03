# Handover: status as of 2026-11-04

This file is for whoever picks up the work next, human or AI reviewer. It records what changed, why, what was verified, and what is still open. Read it together with `AGENTS.md`, `docs/SAFETY.md` and `docs/ARCHITECTURE.md`.

## Pull requests

| PR | Branch | Content | State |
|---|---|---|---|
| #1 | `bootstrap/paper-trading-foundation` | M0: paper-only breakout scanner, Decimal risk sizing, docs, CI | Merged |
| #7 | `feat/nse-bhavcopy-scan` | Real-data scan from NSE bhavcopy files, `CLAUDE.md` | Merged |
| #8 | `feat/broker-access-handover` | Read-only broker access config, docs, this handover | Merged |
| #9 | `docs/strategy-playbook` | `docs/STRATEGY.md`: agreed strategies, risk mandate, validation rules | Merged |
| #10 | `feat/upstox-data-adapter` | Upstox adjusted daily candles as the default `--scan` source | Merged |

## What was done, in order

1. **Merged #1** after reviewing the code and confirming CI passed.
2. **Added `CLAUDE.md`**, guidance for Claude Code. It imports `AGENTS.md` instead of duplicating it.
3. **Real-data scanner (#7).** `src/gt_invest/bhavcopy.py` downloads NSE's official daily files. `python -m gt_invest --scan` runs the existing breakout rules across all mainboard (`EQ`) stocks.
   - The run on 2026-11-03 covered 2,744 stocks. 1,873 had enough clean history (≥201 sessions), and 2 were candidates. This is scanner output, not a recommendation or a backtest.
   - Why stocks were skipped: 413 had a missing session, 392 were new listings, and 66 had a >25% overnight gap (unadjusted split or bonus).
4. **Broker research.** Both brokers' current offerings were checked against official docs; the decisions are below.
5. **Upstox Analytics Token** created by the user and stored in the local `.env`, which is git-ignored.
   - Verified working.
   - Verified that daily candles are split-adjusted. JSWDULUX before its 1:10 split on 2026-10-22: NSE file close ₹2,994.80, Upstox close ₹299.50. BANSALWIRE before its split on 2026-10-16: NSE ₹315.60, Upstox ₹63.10.
6. **Groww official MCP** connected in Claude Code. The server exposes 31 tools, all of them reads or calculators. None places, modifies or cancels orders (as of 2026-11-03).
   - Those 31 are allow-listed in `.claude/settings.json`, and likely order-tool names are denied in case Groww adds them.
   - A read-only portfolio fetch was verified. **No holdings data is stored in this repo.**
7. **Upstox data adapter.** `src/gt_invest/upstox.py` maps the 2,749 `EQ` symbols in Upstox's instrument file to `NSE_EQ|<ISIN>` keys and downloads each stock's split-adjusted daily candles. It is now the default for `--scan`; NSE files remain available with `--source nse`.
   - Upstox's Nov 2 RELIANCE candle matched the NSE file exactly (OHLC and volume).
   - The Analytics Token gets 401 on every market-quote endpoint (`/v2/market-quote/quotes`, `/v2` and `/v3` `ohlc`). Only historical candles work, so there is no cheap batch call to pre-filter stocks; each stock costs one request.
   - Upstox's Cloudflare front rejects urllib's default User-Agent (error 1010); `gt-invest/0.1` works.
   - Live scan of the Nov 3 session (run 00:55–01:27 IST, 31 min): 2,744 stocks, 2,287 with enough clean history (NSE files: 1,873), 3 candidates. The NSE scan of the same session found 2 of them with identical closes and stops; the third, SPECTRUM, lacked enough clean NSE history. Scanner output, not a recommendation or a backtest.

## Decisions and why

| Decision | Reason |
|---|---|
| Evening scan, next-morning execution, no intraday | Matches `docs/PRODUCT.md`. A closing-price signal can't be filled at that close. |
| Upstox Analytics Token for market data | Read-only, cannot trade, valid 1 year, free, needs no OAuth redirect or static IP for market data, and history is split-adjusted. |
| Full Upstox OAuth app and static IP deferred to M5 | Only order APIs need them. Exchange rules since 2026-04-01: registered static IP, ≤10 orders/sec, no plain market orders. |
| Groww via its official MCP, read tools only | The existing ~₹1 lakh portfolio is in Groww. The MCP is free; the Groww Trade API costs ₹499/month and isn't needed just to read holdings. |
| Upstox MCP not used | The portfolio isn't at Upstox, and the token already covers data. |
| `upstox-skill` plugin must not be installed | It places live orders, which `AGENTS.md` rules 3 and 5 forbid. |
| Groww DDPI stays off | Without it, nothing connected to the account can sell holdings. |

## Known issues and open questions

1. **NSE downloader User-Agent (#7).** NSE's archive doesn't respond to non-browser clients, so `bhavcopy.fetch()` sends `User-Agent: Mozilla/5.0`. Upstox is now the default, so this only affects the `--source nse` fallback. **Reviewer decision:** keep the fallback, or delete `bhavcopy.py` except `histories()`.
2. **Momentum lookback is off by one.** `strategy.py` uses `past[-63]`, which is 64 sessions before the signal day.
3. **Missing test:** a volume ratio between 1.0× and 1.5× (should be rejected).
4. Holiday 404s are not cached, so about 10 cheap requests repeat each run.
5. `bhavcopy.histories()` only returns symbols listed on the latest day. That's fine for a daily scan, but backtests need history for delisted names too.
6. It's unverified whether Upstox candles are also adjusted for dividends (only splits were checked).
7. The Groww deny list uses **guessed** names. A tool Groww adds later is neither allowed nor denied, so Claude Code's permission mode decides. Re-check the tool list after Groww updates.
8. **Local-only setup that isn't in the repo:** the `.env` token, and the Groww MCP registration in `~/.claude.json`. To register Groww on a new machine, run `claude mcp add --transport http groww https://mcp.groww.in/mcp`, then log in via `/mcp`.
9. **Upstox publishes daily candles late.** Nov 3's candles were missing from the historical endpoint at 00:52 IST on Nov 4 (the intraday endpoint was already empty) and present for all 2,744 stocks by 00:55. One observation only. Until it is confirmed, an evening scan covers the previous session; `by_day()` drops a session that is only partly published.
10. **A fresh Upstox scan takes about 30 minutes** (~2,750 requests against 2,000 per 30 min). Re-runs within 2 hours reuse the cache. The cache is short on purpose, since Upstox re-adjusts history after a split.

## How to verify

```bash
python -m pip install -e .
python -m unittest discover -s tests -v     # 18 tests, offline
python -m gt_invest --demo                  # synthetic, no network
python -m gt_invest --scan                  # Upstox data; needs the .env token, ~30 min fresh
python -m gt_invest --scan --source nse     # NSE files; first run ~3 min, ~40 MB cache in data/raw/bhavcopy/
```

## Proposed next steps

1. **Confirm when Upstox publishes a session's daily candles** (known issue 9; once seen at ~00:55 IST), and schedule the scan after it.
2. **Holdings trend check:** run the scanner's trend rules on the Groww holdings and label each as uptrend, weakening or downtrend. Symbols are passed in at runtime and never stored.
3. Fix known issues 2 and 3, with regression tests.
4. **M2 backtest (#3):** fills at the next session's prices, costs, slippage, survivorship controls, and comparison with Nifty.

## Review checklist for an outside reviewer

- [ ] No credentials, tokens, holdings or account data anywhere in the diff or history.
- [ ] Nothing in the repo can place, modify or cancel orders.
- [ ] `.claude/settings.json` allow list contains only read tools, and the deny list covers order actions.
- [ ] The docs (`README.md`, `AGENTS.md`, `CLAUDE.md`, `docs/*`) agree with each other and with the code.
- [ ] Known issue 1 (keep or drop the NSE fallback) has been decided.
- [ ] Next steps are in a sensible order.
