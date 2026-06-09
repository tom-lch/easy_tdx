"""KDJ 金叉策略。

K 上穿 D 且 J < 20（低位金叉）买入，K 下穿 D 且 J > 80（高位死叉）卖出。

用法::

    easy-tdx backtest SZ 000001 --strategy-file strategies/kdj_golden.py --table
"""

from easy_tdx.backtest import Strategy, crossover
from easy_tdx import MyTT


class KDJStrategy(Strategy):
    """KDJ 金叉策略。"""

    def init(self) -> None:
        self.k, self.d, self.j = self.I(
            MyTT.KDJ, self.data.close, self.data.high, self.data.low
        )
        self.k_cross_up = crossover(self.k, self.d)
        self.k_cross_down = crossover(self.d, self.k)

    def next(self) -> None:
        j_val = self.j[self._bar_index]

        if self.k_cross_up[self._bar_index] and j_val < 20 and self.position["size"] == 0:
            self.buy(size=0)
        elif self.k_cross_down[self._bar_index] and j_val > 80 and self.position["size"] > 0:
            self.sell(size=0)
