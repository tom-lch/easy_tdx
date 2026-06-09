"""双均线交叉策略。

MA5 上穿 MA20（金叉）全仓买入，MA5 下穿 MA20（死叉）全部卖出。

用法::

    easy-tdx backtest SZ 000001 --strategy-file strategies/ma_cross.py --table
"""

from easy_tdx.backtest import Strategy, crossover
from easy_tdx import MyTT


class MACrossStrategy(Strategy):
    """双均线交叉策略。"""

    def init(self) -> None:
        self.ma5 = self.I(MyTT.MA, self.data.close, 5)
        self.ma20 = self.I(MyTT.MA, self.data.close, 20)
        self.golden = crossover(self.ma5, self.ma20)
        self.death = crossover(self.ma20, self.ma5)

    def next(self) -> None:
        if self.golden[self._bar_index] and self.position["size"] == 0:
            self.buy(size=0)
        elif self.death[self._bar_index] and self.position["size"] > 0:
            self.sell(size=0)
