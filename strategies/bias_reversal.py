"""乖离率反转策略。

6 日乖离率低于 -3%（超跌）买入，高于 3%（超涨）卖出。
适合震荡市。

用法::

    easy-tdx backtest SZ 000001 --strategy-file strategies/bias_reversal.py --table
"""

from easy_tdx.backtest import Strategy
from easy_tdx import MyTT


class BIAStrategy(Strategy):
    """乖离率反转策略。"""

    def init(self) -> None:
        # BIAS 返回 3 个数组: BIAS6, BIAS12, BIAS24，只取 6 日
        self.bias6, _, _ = self.I(MyTT.BIAS, self.data.close, 6)

    def next(self) -> None:
        val = float(self.bias6[self._bar_index])

        if val < -3 and self.position["size"] == 0:
            self.buy(size=0)
        elif val > 3 and self.position["size"] > 0:
            self.sell(size=0)
