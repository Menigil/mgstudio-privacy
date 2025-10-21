from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from typing import List, Optional

import ccxt  # type: ignore
import pandas as pd


DAY_MS = 24 * 60 * 60 * 1000


@dataclass(frozen=True)
class MarketDataRequest:
    exchange: str
    symbol: str  # e.g., "BTC/USDT"
    timeframe: str  # e.g., "1h", "4h", "1d"
    lookback_days: int = 120


def _build_exchange(exchange_name: str) -> ccxt.Exchange:
    name = exchange_name.lower().strip()
    if not hasattr(ccxt, name):
        raise ValueError(f"Unknown exchange: {exchange_name}")
    exchange_class = getattr(ccxt, name)
    exchange: ccxt.Exchange = exchange_class({"enableRateLimit": True})
    return exchange


def _paginate_ohlcv(
    exchange: ccxt.Exchange,
    symbol: str,
    timeframe: str,
    since_ms: int,
    max_bars: int,
    limit_per_call: int = 1000,
) -> List[List[float]]:
    """Fetch OHLCV in multiple requests until we reach max_bars or data ends."""
    all_rows: List[List[float]] = []
    tf_ms = int(exchange.parse_timeframe(timeframe) * 1000)
    cursor = since_ms

    for _ in range(50):  # hard cap pages for safety
        batch = exchange.fetch_ohlcv(symbol, timeframe, since=cursor, limit=limit_per_call)
        if not batch:
            break
        # Avoid duplicates when the last timestamp equals the cursor
        if all_rows and batch[0][0] <= all_rows[-1][0]:
            batch = [row for row in batch if row[0] > all_rows[-1][0]]
        all_rows.extend(batch)
        if len(all_rows) >= max_bars:
            break
        # advance cursor to just after the last candle
        cursor = batch[-1][0] + tf_ms
    return all_rows


def fetch_ohlcv_dataframe(req: MarketDataRequest) -> pd.DataFrame:
    """Fetch OHLCV and return a DataFrame with columns: Open, High, Low, Close, Volume."""
    exchange = _build_exchange(req.exchange)
    exchange.load_markets()

    # Estimate how many bars are needed from lookback days
    seconds_per_bar = exchange.parse_timeframe(req.timeframe)
    bars_needed = int(ceil(req.lookback_days * 24 * 60 * 60 / seconds_per_bar)) + 5

    since_ms = exchange.milliseconds() - req.lookback_days * DAY_MS
    rows = _paginate_ohlcv(exchange, req.symbol, req.timeframe, since_ms, bars_needed)

    if not rows:
        raise RuntimeError("No OHLCV data returned. Try a different symbol/timeframe.")

    df = pd.DataFrame(rows, columns=["timestamp", "Open", "High", "Low", "Close", "Volume"]).astype(
        {"timestamp": "int64", "Open": float, "High": float, "Low": float, "Close": float, "Volume": float}
    )
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    df.set_index("timestamp", inplace=True)

    # Drop possible duplicate indices and ensure sorted ascending
    df = df[~df.index.duplicated(keep="last")].sort_index()

    return df
