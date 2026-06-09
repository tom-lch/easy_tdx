"""布林带突破策略。

收盘价跌破下轨买入，突破上轨卖出。

用法::

    easy-tdx backtest SZ 000001 --strategy-file strategies/bollinger_breakout.py --table
"""

from easy_tdx.backtest import Strategy
from easy_tdx import MyTT


class BollingerStrategy(Strategy):
    """布林带突破策略。"""

    def init(self) -> None:
        self.upper, self.mid, self.lower = self.I(MyTT.BOLL, self.data.close, 20)

    def next(self) -> None:
        cur = self.data.close[0]
        lower = self.lower[self._bar_index]
        upper = self.upper[self._bar_index]

        if cur <= lower and self.position["size"] == 0:
            self.buy(size=0)
        elif cur >= upper and self.position["size"] > 0:
            self.sell(size=0)
