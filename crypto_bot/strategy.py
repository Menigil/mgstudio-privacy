from __future__ import annotations

from typing import Literal, Tuple

import numpy as np
import pandas as pd
from backtesting import Strategy
from backtesting.lib import crossover


def sma(values: pd.Series | np.ndarray, window: int) -> np.ndarray:
    series = pd.Series(values)
    return series.rolling(window).mean().to_numpy()


class SmaCrossoverStrategy(Strategy):
    """Simple SMA crossover: buy on golden cross, sell on death cross."""

    n_fast: int = 10
    n_slow: int = 21

    def init(self) -> None:
        self.sma_fast = self.I(sma, self.data.Close, int(self.n_fast))
        self.sma_slow = self.I(sma, self.data.Close, int(self.n_slow))

    def next(self) -> None:
        if crossover(self.sma_fast, self.sma_slow):
            # Go long on golden cross
            if self.position.is_short:
                self.position.close()
            if not self.position.is_long:
                self.buy()
        elif crossover(self.sma_slow, self.sma_fast):
            # Go short on death cross
            if self.position.is_long:
                self.position.close()
            if not self.position.is_short:
                self.sell()


def last_cross_signal(
    close: pd.Series, fast_window: int, slow_window: int
) -> Tuple[Literal["cross_up", "cross_down", "none"], pd.Series, pd.Series]:
    """Return last cross signal and the two SMAs.

    - cross_up: fast crossed above slow on the last bar
    - cross_down: fast crossed below slow on the last bar
    - none: no cross on the last bar
    """
    fast = close.rolling(fast_window).mean()
    slow = close.rolling(slow_window).mean()

    if len(close) < max(fast_window, slow_window) + 2:
        return "none", fast, slow

    prev_fast, prev_slow = fast.iloc[-2], slow.iloc[-2]
    curr_fast, curr_slow = fast.iloc[-1], slow.iloc[-1]

    if np.isnan([prev_fast, prev_slow, curr_fast, curr_slow]).any():
        return "none", fast, slow

    if prev_fast <= prev_slow and curr_fast > curr_slow:
        return "cross_up", fast, slow
    if prev_fast >= prev_slow and curr_fast < curr_slow:
        return "cross_down", fast, slow
    return "none", fast, slow
