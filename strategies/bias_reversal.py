"""乖离率反转策略。

乖离率低于阈值（超跌）买入，乖离率高于阈值（超涨）卖出。
适合震荡市。

用法::

    easy-tdx backtest SZ 000001 --strategy-file strategies/bias_reversal.py --table
"""

from easy_tdx.backtest import Strategy
from easy_tdx import MyTT


class BIAStrategy(Strategy):
    """乖离率反转策略。"""

    def init(self) -> None:
        self.bias = self.I(MyTT.BIAS, self.data.close, 6)

    def next(self) -> None:
        val = self.bias[self._bar_index]

        if val < -3 and self.position["size"] == 0:
            self.buy(size=0)
        elif val > 3 and self.position["size"] > 0:
            self.sell(size=0)
