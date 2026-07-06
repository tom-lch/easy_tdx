"""获取 K 线数据命令（支持全部周期）。"""

import struct

from .._binary import unpack_from
from ..codec.datetime_ import get_datetime
from ..codec.price import get_price
from ..codec.volume import get_volume
from ..models.bar import SecurityBar
from ..models.enums import KlineCategory, Market
from .base import BaseCommand


class GetSecurityBarsCmd(BaseCommand[list[SecurityBar]]):
    """获取指定股票的 K 线数据。

    Args:
        market:   市场（SH/SZ）
        code:     6位股票代码（字符串）
        category: K线周期
        start:    起始行（0 = 最新；分页时递增）
        count:    返回条数（最多 800）
    """

    def __init__(
        self,
        market: Market,
        code: str,
        category: KlineCategory,
        start: int,
        count: int = 800,
    ) -> None:
        self.market = market
        self.code = code.encode("utf-8")
        self.category = category
        self.start = start
        self.count = count

    def build_request(self) -> bytes:
        # Header (12 bytes) + Payload (28 bytes) = 40 bytes
        return struct.pack(
            "<HIHHHH6sHHHHIIH",
            0x010C,
            0x01016408,
            0x001C,
            0x001C,
            0x052D,
            int(self.market),
            self.code,
            int(self.category),
            1,
            self.start,
            self.count,
            0,
            0,
            0,
        )

    def parse_response(self, body: bytes) -> list[SecurityBar]:
        (ret_count,) = unpack_from("<H", body, 0, "security_bars header")
        pos = 2
        bars: list[SecurityBar] = []
        pre_diff_base = 0
        cat = int(self.category)

        # 服务器偶发返回的 ret_count 与 body 实际长度不匹配（pytdx/mootdx 均
        # 有类似报告）：ret_count 撒谎或网络帧粘包/截断，循环到中途 pos 已
        # 读到底（"剩余 0 字节"）。改用"取 min(ret_count, body 可解析条数)"
        # 策略——TdxDecodeError 视为记录边界，提前结束循环并丢弃残缺尾记录，
        # 而不是让整批数据 500。调用方拿到的是完整记录（少几根 K 线比全崩好）。
        for _ in range(ret_count):
            record_start = pos
            try:
                year, month, day, hour, minute, pos = get_datetime(cat, body, pos)

                open_diff, pos = get_price(body, pos)
                close_diff, pos = get_price(body, pos)
                high_diff, pos = get_price(body, pos)
                low_diff, pos = get_price(body, pos)

                vol, pos = get_volume(body, pos)
                amount, pos = get_volume(body, pos)
            except Exception:
                # 残缺尾记录：body 已读到底或字段不完整，丢弃本条并停止。
                # 不重新抛出—— degrade gracefully，返回已解析的完整记录。
                break

            # 差分还原（与 pytdx 完全一致）
            open_abs = open_diff + pre_diff_base
            close_abs = open_abs + close_diff
            high_abs = open_abs + high_diff
            low_abs = open_abs + low_diff
            pre_diff_base = open_abs + close_diff

            bars.append(
                SecurityBar(
                    open=open_abs / 1000.0,
                    close=close_abs / 1000.0,
                    high=high_abs / 1000.0,
                    low=low_abs / 1000.0,
                    vol=vol,
                    amount=amount,
                    year=year,
                    month=month,
                    day=day,
                    hour=hour,
                    minute=minute,
                    _raw=body[record_start:pos],
                )
            )

        return bars


class GetIndexBarsCmd(GetSecurityBarsCmd):
    """获取指数 K 线。

    请求格式与股票 K 线相同，但响应每条记录在 vol+amt 后多 4 字节
    （上涨家数 uint16 + 下跌家数 uint16），必须跳过否则后续记录错位。
    """

    def parse_response(self, body: bytes) -> list[SecurityBar]:
        (ret_count,) = unpack_from("<H", body, 0, "security_bars header")
        pos = 2
        bars: list[SecurityBar] = []
        pre_diff_base = 0
        cat = int(self.category)

        # 同 GetSecurityBarsCmd：ret_count 与 body 实际长度偶发不匹配，
        # 残缺尾记录提前 break，详见父类同名注释。
        for _ in range(ret_count):
            record_start = pos
            try:
                year, month, day, hour, minute, pos = get_datetime(cat, body, pos)

                open_diff, pos = get_price(body, pos)
                close_diff, pos = get_price(body, pos)
                high_diff, pos = get_price(body, pos)
                low_diff, pos = get_price(body, pos)

                vol, pos = get_volume(body, pos)
                amount, pos = get_volume(body, pos)

                # 指数记录额外 4 字节：上涨家数 + 下跌家数（各 uint16 LE）
                pos += 4
            except Exception:
                break

            open_abs = open_diff + pre_diff_base
            close_abs = open_abs + close_diff
            high_abs = open_abs + high_diff
            low_abs = open_abs + low_diff
            pre_diff_base = open_abs + close_diff

            bars.append(
                SecurityBar(
                    open=open_abs / 1000.0,
                    close=close_abs / 1000.0,
                    high=high_abs / 1000.0,
                    low=low_abs / 1000.0,
                    vol=vol,
                    amount=amount,
                    year=year,
                    month=month,
                    day=day,
                    hour=hour,
                    minute=minute,
                    _raw=body[record_start:pos],
                )
            )

        return bars
