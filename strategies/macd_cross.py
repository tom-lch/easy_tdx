"""MACD 金叉死叉策略。

DIF 上穿 DEA（金叉）买入，DIF 下穿 DEA（死叉）卖出。

用法::

    easy-tdx backtest SZ 000001 --strategy-file strategies/macd_cross.py --table
"""

from easy_tdx.backtest import Strategy, crossover
from easy_tdx import MyTT


class MACDStrategy(Strategy):
    """MACD 金叉死叉策略。"""

    def init(self) -> None:
        self.dif, self.dea, self.hist = self.I(MyTT.MACD, self.data.close)
        self.golden = crossover(self.dif, self.dea)
        self.death = crossover(self.dea, self.dif)

    def next(self) -> None:
        if self.golden[self._bar_index] and self.position["size"] == 0:
            self.buy(size=0)
        elif self.death[self._bar_index] and self.position["size"] > 0:
            self.sell(size=0)
