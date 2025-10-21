from __future__ import annotations

import time
from datetime import datetime, timezone

import pandas as pd
import typer
from rich.console import Console

from .backtest_runner import print_backtest_summary, run_backtest
from .data import MarketDataRequest, fetch_ohlcv_dataframe
from .strategy import last_cross_signal
from .telegram_notify import send_telegram_message

app = typer.Typer(help="Crypto trading MVP CLI: backtest and monitor signals.")
console = Console()


@app.command()
def backtest(
    exchange: str = typer.Option("binance", help="Exchange id as in ccxt (e.g., binance, bybit, kucoin)"),
    symbol: str = typer.Option("BTC/USDT", help="Symbol in base/quote format"),
    timeframe: str = typer.Option("1h", help="OHLCV timeframe (e.g., 5m, 1h, 4h, 1d)"),
    days: int = typer.Option(120, min=1, help="Lookback window in days"),
    fast: int = typer.Option(10, min=2, help="Fast SMA window"),
    slow: int = typer.Option(21, min=3, help="Slow SMA window (must be > fast)"),
    cash: float = typer.Option(10_000.0, help="Initial cash for backtest"),
    commission: float = typer.Option(0.0010, help="Per-trade commission as fraction"),
) -> None:
    if slow <= fast:
        typer.echo("--slow must be greater than --fast", err=True)
        raise typer.Exit(code=1)

    console.rule(f"Backtest {symbol} @ {timeframe} on {exchange}")

    req = MarketDataRequest(exchange=exchange, symbol=symbol, timeframe=timeframe, lookback_days=days)
    df = fetch_ohlcv_dataframe(req)

    # Ensure required columns casing for backtesting.py
    df = df[["Open", "High", "Low", "Close", "Volume"]]

    if len(df) < slow * 3:
        typer.echo(f"Not enough data fetched ({len(df)} bars) for SMA({slow}). Try increasing --days.", err=True)
        raise typer.Exit(code=1)

    stats = run_backtest(df, fast_window=fast, slow_window=slow, initial_cash=cash, commission=commission)
    print_backtest_summary(stats)


@app.command()
def monitor(
    exchange: str = typer.Option("binance", help="Exchange id as in ccxt"),
    symbol: str = typer.Option("BTC/USDT", help="Symbol in base/quote format"),
    timeframe: str = typer.Option("1h", help="OHLCV timeframe"),
    fast: int = typer.Option(10, min=2, help="Fast SMA window"),
    slow: int = typer.Option(21, min=3, help="Slow SMA window (must be > fast)"),
    interval: int = typer.Option(60, min=10, help="Polling interval in seconds"),
    once: bool = typer.Option(False, help="Run a single check and exit"),
    notify: bool = typer.Option(True, help="Send Telegram notification when crosses occur"),
) -> None:
    if slow <= fast:
        typer.echo("--slow must be greater than --fast", err=True)
        raise typer.Exit(code=1)

    last_signal: str | None = None

    def check_once() -> None:
        nonlocal last_signal
        req = MarketDataRequest(exchange=exchange, symbol=symbol, timeframe=timeframe, lookback_days=30)
        df = fetch_ohlcv_dataframe(req)
        close: pd.Series = df["Close"]
        signal, fast_sma, slow_sma = last_cross_signal(close, fast_window=fast, slow_window=slow)
        ts = df.index[-1].to_pydatetime()
        ts_str = ts.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

        console.print(
            f"[{ts_str}] {symbol} {timeframe} | last={close.iloc[-1]:.2f} | fast={fast_sma.iloc[-1]:.2f} slow={slow_sma.iloc[-1]:.2f} | signal={signal}"
        )

        if signal in ("cross_up", "cross_down") and signal != last_signal:
            direction = "BUY (golden cross)" if signal == "cross_up" else "SELL (death cross)"
            text = f"{symbol} {timeframe}: {direction} at {close.iloc[-1]:.4f} ({ts_str})"
            if notify:
                send_telegram_message(text)
            last_signal = signal

    if once:
        check_once()
        return

    console.rule(f"Monitoring {symbol} @ {timeframe} on {exchange} | fast={fast} slow={slow}")
    while True:
        check_once()
        time.sleep(interval)


if __name__ == "__main__":
    app()
