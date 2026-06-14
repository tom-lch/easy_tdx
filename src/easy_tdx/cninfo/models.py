"""巨潮资讯网（cninfo）数据模型。"""

from __future__ import annotations

from dataclasses import dataclass

from easy_tdx.exceptions import TdxError


@dataclass(frozen=True)
class Announcement:
    """单条公告记录。

    巨潮公告检索接口返回的标准化结构。
    """

    title: str
    type: str
    date: str  # YYYY-MM-DD
    url: str


class CninfoError(TdxError):
    """巨潮数据请求或解析失败。"""
