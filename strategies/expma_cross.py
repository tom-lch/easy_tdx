"""EXPMA 均线交叉策略。

EMA12 上穿 EMA50 买入，EMA12 下穿 EMA50 卖出。
与简单均线相比，EMA 对近期价格更敏感。

用法::

    easy-tdx backtest SZ 000001 --strategy-file strategies/expma_cross.py --table
"""

from easy_tdx.backtest import Strategy, crossover
from easy_tdx import MyTT


class EXPMAStrategy(Strategy):
    """EXPMA 指数均线交叉策略。"""

    def init(self) -> None:
        self.ema12, self.ema50 = self.I(MyTT.EXPMA, self.data.close, 12, 50)
        self.golden = crossover(self.ema12, self.ema50)
        self.death = crossover(self.ema50, self.ema12)

    def next(self) -> None:
        if self.golden[self._bar_index] and self.position["size"] == 0:
            self.buy(size=0)
        elif self.death[self._bar_index] and self.position["size"] > 0:
            self.sell(size=0)
