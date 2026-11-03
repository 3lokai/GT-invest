"""Official NSE daily bhavcopy (UDiFF format, published since July 2024) -> Candles.

Free public archive, no login. Read-only: this module only downloads files.
"""
import csv
import io
import time
import urllib.error
import urllib.request
import zipfile
from datetime import date, timedelta
from pathlib import Path

from .models import Candle

URL = "https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_{:%Y%m%d}_F_0000.csv.zip"
CACHE = Path("data/raw/bhavcopy")
# Mainboard rolling settlement only; excludes SME (SM/ST) and trade-for-trade surveillance (BE/BZ).
SERIES = "EQ"
# EQ price bands are at most 20%, so a bigger overnight move means an unadjusted split/bonus.
# ponytail: we cut history at the gap instead of adjusting; add corporate-action data to keep it.
MAX_GAP = 0.25


def fetch(day: date, cache: Path = CACHE) -> bytes | None:
    """Zipped bhavcopy for one day, or None if NSE has none (holiday or not yet published)."""
    path = cache / f"{day:%Y%m%d}.zip"
    if path.exists():
        return path.read_bytes()
    request = urllib.request.Request(URL.format(day), headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = response.read()
    except urllib.error.HTTPError as e:
        if e.code == 404:  # not cached: today's file may simply not be out yet
            return None
        raise
    cache.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    time.sleep(0.5)  # be polite to the public archive
    return data


def parse(data: bytes) -> list[Candle]:
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        text = z.read(z.namelist()[0]).decode()
    return [
        Candle(
            session=r["TradDt"], symbol=r["TckrSymb"],
            open=float(r["OpnPric"]), high=float(r["HghPric"]),
            low=float(r["LwPric"]), close=float(r["ClsPric"]),
            volume=int(r["TtlTradgVol"]),
        )
        for r in csv.DictReader(io.StringIO(text))
        if r["SctySrs"] == SERIES
    ]


def load(end: date, sessions: int, cache: Path = CACHE) -> list[list[Candle]]:
    """The last `sessions` trading days up to `end`, oldest first, one list of candles per day."""
    days: list[list[Candle]] = []
    day = end
    while len(days) < sessions:
        if day < date(2024, 7, 8):
            raise ValueError("UDiFF bhavcopy starts July 2024; older files use another format")
        if day.weekday() < 5 and (data := fetch(day, cache)) is not None:
            days.append(parse(data))
        day -= timedelta(days=1)
    return days[::-1]


def histories(days: list[list[Candle]]) -> dict[str, list[Candle]]:
    """Per symbol listed on the latest day: its trailing run of clean, consecutive sessions.

    The run stops where the symbol was missing (suspended, moved series) or gapped
    more than MAX_GAP, so the scanner never sees a broken price series.
    """
    by_day = [{c.symbol: c for c in day} for day in days]
    out: dict[str, list[Candle]] = {}
    for symbol, latest in by_day[-1].items():
        run = [latest]
        for day in reversed(by_day[:-1]):
            prev = day.get(symbol)
            if prev is None or abs(run[-1].open / prev.close - 1) > MAX_GAP:
                break
            run.append(prev)
        out[symbol] = run[::-1]
    return out
