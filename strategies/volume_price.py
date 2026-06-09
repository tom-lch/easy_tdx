"""量价配合策略。

放量上涨（成交量 > MA(vol,5) 且收阳线）买入，
缩量下跌（成交量 < MA(vol,5) 且收阴线）且持仓盈利时卖出。

用法::

    easy-tdx backtest SZ 000001 --strategy-file strategies/volume_price.py --table
"""

from easy_tdx.backtest import Strategy
from easy_tdx import MyTT


class VolumePriceStrategy(Strategy):
    """量价配合策略。"""

    def init(self) -> None:
        self.vol_ma = self.I(MyTT.MA, self.data.vol, 5)

    def next(self) -> None:
        cur_close = self.data.close[0]
        cur_open = self.data.open[0]
        cur_vol = self.data.vol[0]
        avg_vol = self.vol_ma[self._bar_index]

        is_yang = cur_close > cur_open   # 阳线
        is_yin = cur_close < cur_open    # 阴线
        is_vol_up = cur_vol > avg_vol    # 放量
        is_vol_down = cur_vol < avg_vol  # 缩量

        if is_yang and is_vol_up and self.position["size"] == 0:
            self.buy(size=0)
        elif is_yin and is_vol_down and self.position["size"] > 0:
            self.sell(size=0)
