"""Upstox daily candles (split/bonus adjusted) -> Candles, via the read-only Analytics Token.

Read-only: this module only downloads. It uses the historical-candle endpoint and the public
instrument file; the Analytics Token gets 401 on market-quote endpoints.
"""
import gzip
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import deque
from datetime import date, datetime, timedelta
from pathlib import Path

from .models import Candle

INSTRUMENTS_URL = "https://assets.upstox.com/market-quote/instruments/exchange/NSE.json.gz"
CANDLES_URL = "https://api.upstox.com/v3/historical-candle/{key}/days/1/{to}/{frm}"
CACHE = Path("data/raw/upstox")
SERIES = "EQ"  # same mainboard series as bhavcopy.SERIES
# Cloudflare in front of Upstox rejects urllib's default User-Agent.
HEADERS = {"Accept": "application/json", "User-Agent": "gt-invest/0.1"}
# (window seconds, max requests) for historical candles, from Upstox's rate-limit page.
LIMITS = ((1, 50), (60, 500), (1800, 2000))
# Upstox re-adjusts past candles after a split, so cached candles are only a resume buffer.
# ponytail: mtime TTL; key by publish date if backtests need permanent history.
CANDLE_TTL = 2 * 3600
INSTRUMENT_TTL = 12 * 3600
# Upstox publishes a session's candles symbol by symbol; a thinner last day is still filling in.
MIN_DAY_COVERAGE = 0.9

_sent: deque[float] = deque(maxlen=max(n for _, n in LIMITS))


def token(env_file: Path = Path(".env")) -> str:
    """UPSTOX_ANALYTICS_TOKEN from the environment or the git-ignored .env. Never printed."""
    if value := os.environ.get("UPSTOX_ANALYTICS_TOKEN"):
        return value
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            key, _, value = line.partition("=")
            if key.strip() == "UPSTOX_ANALYTICS_TOKEN" and value.strip():
                return value.strip()
    raise SystemExit("UPSTOX_ANALYTICS_TOKEN is not set; see .env.example")


def _fresh(path: Path, ttl: float) -> bool:
    return path.exists() and time.time() - path.stat().st_mtime < ttl


def _throttle(sent: deque = _sent, clock=time.monotonic, sleep=time.sleep) -> None:
    """Wait until one more request fits inside every window in LIMITS."""
    for window, limit in LIMITS:
        if len(sent) >= limit and (wait := sent[-limit] + window - clock()) > 0:
            if wait > 10:
                print(f"  waiting {wait:.0f} s for the Upstox rate limit", file=sys.stderr)
            sleep(wait)
    sent.append(clock())


def parse_instruments(data: bytes) -> dict[str, str]:
    """Mainboard EQ trading symbol -> instrument key (NSE_EQ|<ISIN>)."""
    return {
        r["trading_symbol"]: r["instrument_key"]
        for r in json.loads(gzip.decompress(data))
        if r.get("segment") == "NSE_EQ" and r.get("instrument_type") == SERIES
    }


def instruments(cache: Path = CACHE) -> dict[str, str]:
    """Today's instrument list. ponytail: current listings only, so not point-in-time for backtests."""
    path = cache / "NSE.json.gz"
    if not _fresh(path, INSTRUMENT_TTL):
        request = urllib.request.Request(INSTRUMENTS_URL, headers=HEADERS)
        with urllib.request.urlopen(request, timeout=60) as response:
            data = response.read()
        cache.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    return parse_instruments(path.read_bytes())


def _cdn_bust() -> int:
    """Extra days of history to request, different every 15 minutes of the day (0-95).

    Cloudflare in front of Upstox caches each URL for hours (an 11-hour-old copy was seen),
    ignoring query strings and no-cache headers, so a URL first requested before a session was
    published keeps returning it without that session. Moving from_date makes a fresh URL.
    """
    now = datetime.now()
    return (now.hour * 60 + now.minute) // 15


def fetch(key: str, start: date, end: date, auth: str, cache: Path = CACHE, ttl: float = CANDLE_TTL) -> bytes | None:
    """Raw daily-candle JSON for one instrument (may start before `start`), or None if Upstox
    rejects the instrument."""
    path = cache / "candles" / f"{start}_{end}" / f"{key.split('|')[-1]}.json"
    if _fresh(path, ttl):
        return path.read_bytes()
    frm = start - timedelta(days=_cdn_bust())
    url = CANDLES_URL.format(key=urllib.parse.quote(key, safe=""), to=end, frm=frm)
    request = urllib.request.Request(url, headers={**HEADERS, "Authorization": f"Bearer {auth}"})
    _throttle()
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = response.read()
    except urllib.error.HTTPError as e:
        if e.code == 400:  # invalid or unsupported instrument; 401/429 must stop the run
            return None
        raise
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return data


def parse(data: bytes, symbol: str) -> list[Candle]:
    rows = json.loads(data)["data"]["candles"]
    candles = [
        Candle(
            session=r[0][:10], symbol=symbol,  # timestamps are IST midnight, so the date is the session
            open=float(r[1]), high=float(r[2]), low=float(r[3]), close=float(r[4]),
            volume=int(r[5]),
        )
        for r in rows
    ]
    return sorted(candles, key=lambda c: c.session)


def by_day(candles: list[Candle]) -> list[list[Candle]]:
    """Group per-symbol candles into sessions, oldest first, as bhavcopy.load returns them.

    Drops the last session if it is still being published (too few symbols), so the scan
    runs on the newest complete session instead of a fraction of the market.
    """
    sessions: dict[str, list[Candle]] = {}
    for c in candles:
        sessions.setdefault(c.session, []).append(c)
    days = [sessions[s] for s in sorted(sessions)]
    if len(days) >= 2 and len(days[-1]) < MIN_DAY_COVERAGE * len(days[-2]):
        print(f"Skipping {days[-1][0].session}: only {len(days[-1])} of ~{len(days[-2])} stocks "
              "published so far.", file=sys.stderr)
        days.pop()
    return days


def history(symbols: list[str], end: date, sessions: int, cache: Path = CACHE,
            ttl: float = CANDLE_TTL) -> dict[str, list[Candle]]:
    """Per symbol: its last `sessions` daily candles up to `end`, oldest first.

    Symbols missing from the mainboard EQ list (ETFs, SME, BE, delisted) are left out.
    """
    auth = token()
    keys = instruments(cache)
    start = end - timedelta(days=sessions * 7 // 4)  # ~250 sessions a year, plus holidays
    out: dict[str, list[Candle]] = {}
    for i, symbol in enumerate(symbols, 1):
        if symbol in keys and (data := fetch(keys[symbol], start, end, auth, cache, ttl)) is not None:
            out[symbol] = parse(data, symbol)[-sessions:]
        if i % 250 == 0:
            print(f"  {i}/{len(symbols)}", file=sys.stderr)
    return out


def load(end: date, sessions: int, cache: Path = CACHE) -> list[list[Candle]]:
    """The last `sessions` trading days up to `end`, oldest first, one list of candles per day."""
    symbols = sorted(instruments(cache))
    print(f"Upstox: {len(symbols)} stocks, limit {LIMITS[-1][1]} requests per 30 min; a fresh run "
          "takes about 30 minutes, re-runs within 2 hours reuse the cache.", file=sys.stderr)
    runs = history(symbols, end, sessions, cache)
    return by_day([c for run in runs.values() for c in run])[-sessions:]
