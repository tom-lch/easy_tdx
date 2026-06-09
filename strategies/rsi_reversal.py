"""RSI 超买超卖策略。

RSI < 30（超卖）买入，RSI > 70（超买）卖出。

用法::

    easy-tdx backtest SZ 000001 --strategy-file strategies/rsi_reversal.py --table
"""

from easy_tdx.backtest import Strategy
from easy_tdx import MyTT


class RSIStrategy(Strategy):
    """RSI 超买超卖反转策略。"""

    def init(self) -> None:
        self.rsi = self.I(MyTT.RSI, self.data.close, 14)

    def next(self) -> None:
        cur_rsi = self.rsi[self._bar_index]

        if cur_rsi < 30 and self.position["size"] == 0:
            self.buy(size=0)
        elif cur_rsi > 70 and self.position["size"] > 0:
            self.sell(size=0)
