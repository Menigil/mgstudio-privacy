from __future__ import annotations

from typing import Any, Dict

import pandas as pd
from backtesting import Backtest
from rich import box
from rich.console import Console
from rich.table import Table

from .strategy import SmaCrossoverStrategy


def run_backtest(
    price_df: pd.DataFrame,
    fast_window: int = 10,
    slow_window: int = 21,
    initial_cash: float = 10_000.0,
    commission: float = 0.0010,
) -> Dict[str, Any]:
    """Execute a backtest and return stats as a dict."""
    # Backtesting expects columns exactly: Open, High, Low, Close, Volume
    required_cols = {"Open", "High", "Low", "Close", "Volume"}
    if not required_cols.issubset(set(price_df.columns)):
        missing = required_cols - set(price_df.columns)
        raise ValueError(f"Missing required columns: {missing}")

    bt = Backtest(
        price_df,
        SmaCrossoverStrategy,
        cash=initial_cash,
        commission=commission,
        trade_on_close=True,
        exclusive_orders=True,
    )
    stats = bt.run(n_fast=int(fast_window), n_slow=int(slow_window))

    # Convert to plain dict (Stats is a Series-like object)
    return {k: float(v) if hasattr(v, "__float__") else v for k, v in stats.items()}


def print_backtest_summary(stats: Dict[str, Any]) -> None:
    console = Console()

    table = Table(title="SMA Crossover Backtest", box=box.SIMPLE_HEAVY)
    table.add_column("Metric")
    table.add_column("Value", justify="right")

    important_keys = [
        "Start",
        "End",
        "Duration",
        "# Trades",
        "Win Rate [%]",
        "Return [%]",
        "Equity Final [$]",
        "Max. Drawdown [%]",
        "Sharpe Ratio",
        "Sortino Ratio",
        "Calmar Ratio",
        "Avg. Drawdown Duration",
        "Exposure Time [%]",
    ]

    for key in important_keys:
        if key in stats:
            table.add_row(key, str(stats[key]))

    console.print(table)
