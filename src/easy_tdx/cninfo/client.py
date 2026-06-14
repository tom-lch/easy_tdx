"""巨潮资讯网（cninfo）公告检索客户端。

独立于 TDX 协议的 HTTP 数据源（标准库 urllib，零额外依赖）。
公开方法返回 ``pd.DataFrame``，遵循项目 ``get_*`` 约定。

参考实现说明（来自 #19 修复）：

- 巨潮 ``orgId`` 并非统一的 ``gssx0{code}`` 格式（如 601318→9900002221、
  601398→jjxt0000019、688017→9900041602），硬编码会导致大量股票
  （尤其 601xxx 段）返回 ``totalAnnouncement=0``、查不到公告。
- 优先动态查官方映射表，查不到再回退硬编码规则。
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any
from urllib import parse
from urllib import request as urlrequest

import pandas as pd

from .models import Announcement, CninfoError

logger = logging.getLogger(__name__)

# 巨潮公告检索请求固定头（Referer/Origin 必填，否则被反爬拦截）
_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
_STOCK_MAP_URL = "http://www.cninfo.com.cn/new/data/szse_stock.json"
_QUERY_URL = "https://www.cninfo.com.cn/new/hisAnnouncement/query"
_DETAIL_URL = "https://www.cninfo.com.cn/new/disclosure/detail?annoId="

# 模块级 orgId 映射缓存：首次拉取后全程复用（Cpython dict 读写原子，
# 并发下最坏多发一次请求，可接受）
_ORGID_MAP: dict[str, str] = {}


def _ts_to_date(ts: Any) -> str:
    """巨潮 ``announcementTime`` 返回 Unix 毫秒整数，转 ``YYYY-MM-DD``。"""
    if isinstance(ts, (int, float)):
        return datetime.fromtimestamp(ts / 1000).strftime("%Y-%m-%d")
    return str(ts)[:10] if ts else ""


def _http_get_json(url: str, timeout: float = 15.0) -> Any:
    """GET JSON（stdlib urllib，monkeypatch 点）。"""
    req = urlrequest.Request(url, headers={"User-Agent": _UA})
    with urlrequest.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _http_post_form(url: str, payload: dict[str, str], timeout: float = 15.0) -> Any:
    """POST x-www-form-urlencoded，返回 JSON（stdlib urllib，monkeypatch 点）。"""
    data = parse.urlencode(payload).encode("utf-8")
    req = urlrequest.Request(
        url,
        data=data,
        headers={
            "User-Agent": _UA,
            "Content-Type": "application/x-www-form-urlencoded",
            "Referer": "https://www.cninfo.com.cn/new/disclosure",
            "Origin": "https://www.cninfo.com.cn",
        },
        method="POST",
    )
    with urlrequest.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


class CninfoClient:
    """巨潮公告检索客户端（无状态 HTTP，无需 connect/close）。

    用法::

        from easy_tdx.cninfo import CninfoClient

        df = CninfoClient().get_announcements("688017", count=30)
        # → DataFrame[title, type, date, url]
    """

    def __init__(self, *, timeout: float = 15.0) -> None:
        self.timeout = timeout

    # ------------------------------------------------------------------
    # orgId 解析（#19 修复逻辑：动态表 + 三段硬编码 fallback）
    # ------------------------------------------------------------------

    def _fetch_stock_map(self) -> dict[str, str]:
        """拉取官方 szse_stock.json，构建 code→orgId 映射。"""
        try:
            d = _http_get_json(_STOCK_MAP_URL, timeout=self.timeout)
            stock_list = d.get("stockList", []) if isinstance(d, dict) else []
            return {s["code"]: s["orgId"] for s in stock_list}
        except Exception as e:  # noqa: BLE001 — 拉取失败需 graceful fallback
            logger.warning("巨潮 orgId 映射表拉取失败，回退硬编码规则: %s", e)
            return {}

    def _resolve_orgid(self, code: str) -> str:
        """查股票真实 orgId，动态表优先，查不到回退硬编码规则。"""
        global _ORGID_MAP
        if not _ORGID_MAP:
            fetched = self._fetch_stock_map()
            # 只在确实取到数据时写入缓存；空结果保留以便下次重试
            if fetched:
                _ORGID_MAP.update(fetched)
        org = _ORGID_MAP.get(code)
        if org:
            return org
        # fallback：老格式（仅部分老股票如 600519/600036 适用）
        if code.startswith("6"):
            return f"gssh0{code}"
        if code.startswith("8") or code.startswith("4"):
            return f"gsbj0{code}"
        return f"gssz0{code}"

    # ------------------------------------------------------------------
    # 公开 API
    # ------------------------------------------------------------------

    def get_announcements(
        self,
        code: str,
        *,
        count: int = 30,
        page: int = 1,
    ) -> pd.DataFrame:
        """检索指定股票的公告列表。

        Args:
            code: 6 位股票代码（不含市场前缀），如 ``688017``。
            count: 每页数量（即 pageSize）。
            page: 页码（1 起始）。

        Returns:
            ``DataFrame[title, type, date, url]``，按服务器返回顺序（最新在前）。
            无结果时返回空 DataFrame（含列名）。
        """
        rows = self._query_announcements(code, count=count, page=page)
        if not rows:
            return pd.DataFrame(columns=["title", "type", "date", "url"])
        return pd.DataFrame([r.__dict__ for r in rows])

    def _query_announcements(self, code: str, *, count: int, page: int) -> list[Announcement]:
        """POST 公告检索接口，解析为 Announcement 列表。

        整个 HTTP + 解析过程统一捕获异常并转为 ``CninfoError``，避免
        ``announcementTime`` 等字段畸形时 ``_ts_to_date`` 抛出未捕获异常。
        """
        org_id = self._resolve_orgid(code)
        payload = {
            "stock": f"{code},{org_id}",
            "tabName": "fulltext",
            "pageSize": str(count),
            "pageNum": str(page),
            "column": "",
            "category": "",
            "plate": "",
            "seDate": "",
            "searchkey": "",
            "secid": "",
            "sortName": "",
            "sortType": "",
            "isHLtitle": "true",
        }
        try:
            d = _http_post_form(_QUERY_URL, payload, timeout=self.timeout)
            items = d.get("announcements", []) if isinstance(d, dict) else None
            if not items:
                return []

            result: list[Announcement] = []
            for item in items:
                if not isinstance(item, dict):
                    continue
                anno_id = item.get("announcementId", "")
                result.append(
                    Announcement(
                        title=item.get("announcementTitle", ""),
                        type=item.get("announcementTypeName", ""),
                        date=_ts_to_date(item.get("announcementTime")),
                        url=f"{_DETAIL_URL}{anno_id}",
                    )
                )
            return result
        except CninfoError:
            raise
        except Exception as e:  # noqa: BLE001 — HTTP 失败 / JSON 解析 / 日期转换统一转领域异常
            raise CninfoError(f"巨潮公告检索失败: {e}") from e
