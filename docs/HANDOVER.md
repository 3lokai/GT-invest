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
| #11 | `fix/momentum-volume-tests` | Tests pinning the 63-session momentum and the 1.5× volume boundary | Merged |
| #12 | `feat/holdings-trend` | `--trend`, `--latest`, Upstox stale-CDN fix | Merged |
| #13 | `feat/backtest-breakout` | M2 first slice: breakout backtest, ETF exclusion, first report | Merged |

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
8. **Holdings trend check.** `python -m gt_invest --trend SYMBOL ...` labels each chart uptrend, weakening or downtrend from its close and 50/200-session averages. Symbols are typed at runtime (for example from the Groww MCP) and never stored. It describes charts; it is not a sell signal.
9. **Known issues 2 and 3 (#11).** The momentum off-by-one was not a bug (`past[-63]` is exactly 63 sessions back); tests now pin it and the 1.5× volume boundary.
10. **ETFs removed from the universe (#13).** NSE's `EQ` series and Upstox's `EQ` instruments both include ETFs: 356 of the 2,744 "stocks" on Nov 3 were ETFs (ISIN `INF…`), plus 1 `IN9…` security. Both sources now keep only company shares (ISIN `INE…`). Scan counts above, from before this fix, include ETFs.
11. **First backtest (M2 slice, #13).** `python -m gt_invest --backtest` replays the breakout scanner on every NSE file since July 2024, including later-delisted stocks. Report: [`reports/backtest-breakout-v1-2026-11-03.md`](../reports/backtest-breakout-v1-2026-11-03.md).
   - 2025-04-30 to 2026-11-03 (375 sessions), ₹1L plus ₹20k a month, ₹4.8L deposited.
   - **Strategy: ₹4.31L at the end, −11.4% a year money-weighted, max drawdown −27.9%.** Nifty 500 with the same deposits: ₹4.77L, −0.7%, −14.8%.
   - 462 closed trades, 22% winners. Both halves lost money (−7.5%, −9.8% time-weighted), so the loss isn't one bad stretch.
   - Charges were ₹44.8k, about 9% of everything deposited. On the median ₹11k position, ₹20 brokerage + ₹20 DP + GST is ~0.43% per round trip, ~0.65% with STT and stamp duty, before the 0.5% assumed slippage. In 68 trades the position was so small that charges took over 10% of it; some were single shares worth ₹42–63, where ₹47 of fixed charges exceeded the position.
   - First run, before the ETF fix, looked better (−9.6% a year) only because gold and silver ETF breakouts carried the first half.
   - Fills checked by hand against raw NSE data for CHAMBLFERT and KPRMILL.
   - **This is one simulated period, one regime, unadjusted data and no tuning. It says this V1 rule set did badly here; it does not say breakouts can't work.**
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

1. **NSE downloader User-Agent (#7).** NSE's archive doesn't respond to non-browser clients, so `bhavcopy.fetch()` sends `User-Agent: Mozilla/5.0`. **Decided: keep `bhavcopy.py`.** The backtest needs it, because NSE's daily files include stocks later delisted, while Upstox only lists current ones.
2. ~~Momentum lookback is off by one.~~ Not a bug: `past[-63]` is exactly 63 sessions before the signal day. A test now pins it.
3. ~~Missing test for a volume ratio between 1.0× and 1.5×.~~ Added, along with the exact 1.5× boundary (accepted).
4. Holiday 404s are not cached, so about 10 cheap requests repeat each run.
5. `bhavcopy.histories()` only returns symbols listed on the latest day. Fine for a daily scan; the backtest builds its own day-by-day series instead, so delisted names are included there.
6. It's unverified whether Upstox candles are also adjusted for dividends (only splits were checked).
7. The Groww deny list uses **guessed** names. A tool Groww adds later is neither allowed nor denied, so Claude Code's permission mode decides. Re-check the tool list after Groww updates.
8. **Local-only setup that isn't in the repo:** the `.env` token, and the Groww MCP registration in `~/.claude.json`. To register Groww on a new machine, run `claude mcp add --transport http groww https://mcp.groww.in/mcp`, then log in via `/mcp`.
9. **Upstox publish time is unknown.** An earlier note here said Nov 3's candles appeared around 00:55 IST on Nov 4. That was wrong. Cloudflare in front of Upstox caches each candle URL for hours (an 11.4-hour-old copy was served), ignoring query strings and `Cache-Control: no-cache`, and the 00:52 probe hit a stale copy. `upstox.fetch()` now shifts `from_date` by one day per 15-minute slot so every run gets fresh URLs; the probe then returned Nov 3 at 03:52. A stock whose response is still stale drops out of that day's scan, because `histories()` only keeps stocks present on the latest session, and `by_day()` drops a session that is only partly published. `python -m gt_invest --latest` prints the newest published session from three stocks, to measure the publish time.
10. **A fresh Upstox scan takes about 30 minutes** (~2,750 requests against 2,000 per 30 min). Re-runs within 2 hours reuse the cache. The cache is short on purpose, since Upstox re-adjusts history after a split.
11. **Sizing ignores charges.** `size_position` will propose a 1-share position; at small sizes the fixed ₹47 round-trip charges dominate (see the backtest). A minimum position size (for example ₹5,000) is a rule change and needs your approval; it was not added after seeing the result, to avoid fitting to it.
12. **Backtest gap exits flatter crashes.** On unadjusted NSE data a held stock that gaps over 25% is closed at its last price (7 trades), which is right for a split but too kind for a real crash.
13. **Backtest data is short:** about 18 months after warm-up, one regime. Upstox's adjusted history goes back 10 years but only for currently listed stocks (survivorship bias); a second run on it would show a longer, rosier-biased picture.

## How to verify

```bash
python -m pip install -e .
python -m unittest discover -s tests -v     # 30 tests, offline
python -m gt_invest --demo                  # synthetic, no network
python -m gt_invest --scan                  # Upstox data; needs the .env token, ~30 min fresh
python -m gt_invest --scan --source nse     # NSE files; first run ~3 min, ~40 MB cache in data/raw/bhavcopy/
python -m gt_invest --backtest              # ~590 NSE files (~5 min first time), report in reports/
```

## Proposed next steps

1. **Measure when Upstox publishes a session's daily candles** (known issue 9) by running `--latest` every 15 minutes for a few evenings, e.g. crontab `*/15 16-23 * * 1-5 cd <repo> && PYTHONPATH=src python -m gt_invest --latest >> data/raw/upstox/publish-times.log`. Then schedule the scan after it.
2. **Decide known issue 11** (minimum position size) and whether to re-run with it as V2.
3. **M2, rest of #3:** Minervini-style trend/VCP and 3/6-month relative-strength rotation on the same engine; a 10-year run on Upstox data to see other regimes (labelled as survivorship-biased).
4. **M3/M4:** Groww holdings audit and a paper journal with the daily briefing.

## Review checklist for an outside reviewer

- [ ] No credentials, tokens, holdings or account data anywhere in the diff or history.
- [ ] Nothing in the repo can place, modify or cancel orders.
- [ ] `.claude/settings.json` allow list contains only read tools, and the deny list covers order actions.
- [ ] The docs (`README.md`, `AGENTS.md`, `CLAUDE.md`, `docs/*`) agree with each other and with the code.
- [ ] Known issue 1 (keep or drop the NSE fallback) has been decided.
- [ ] Next steps are in a sensible order.
