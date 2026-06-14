"""巨潮（cninfo）模块离线测试 —— mock HTTP，零网络依赖。

覆盖：日期转换、orgId 解析（动态表/三段 fallback）、公告解析、分页、
错误转换、模块导出。
"""

from __future__ import annotations

import json
from typing import Any

import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# 导出
# ---------------------------------------------------------------------------


def test_public_exports() -> None:
    """模块应导出 CninfoClient / Announcement / CninfoError。"""
    from easy_tdx import cninfo

    assert hasattr(cninfo, "CninfoClient")
    assert hasattr(cninfo, "Announcement")
    assert hasattr(cninfo, "CninfoError")


def test_announcement_is_frozen_dataclass() -> None:
    """Announcement 应为 frozen dataclass，含 title/type/date/url。"""
    from easy_tdx.cninfo import Announcement

    a = Announcement(title="t", type="ty", date="2026-06-14", url="http://x")
    assert a.title == "t"
    assert a.type == "ty"
    assert a.date == "2026-06-14"
    assert a.url == "http://x"
    # frozen
    with pytest.raises(Exception):
        a.title = "mutated"  # type: ignore[misc]


def test_cninfo_error_is_exception() -> None:
    from easy_tdx.cninfo import CninfoError
    from easy_tdx.exceptions import TdxError

    assert issubclass(CninfoError, Exception)
    # 回归 #1：CninfoError 必须继承 TdxError，保证全局 except TdxError 覆盖
    assert issubclass(CninfoError, TdxError)


# ---------------------------------------------------------------------------
# 日期转换
# ---------------------------------------------------------------------------


def test_ts_to_date_from_millis() -> None:
    """Unix 毫秒整数应转为 YYYY-MM-DD。"""
    from easy_tdx.cninfo.client import _ts_to_date

    # 1718323200000 ms = 2024-06-14 00:00:00 UTC ≈ 当地日期
    assert _ts_to_date(1718323200000)  # 非空字符串，长度 10
    assert len(_ts_to_date(1718323200000)) == 10


def test_ts_to_date_from_string() -> None:
    """字符串输入应取前 10 字符。"""
    from easy_tdx.cninfo.client import _ts_to_date

    assert _ts_to_date("2026-06-14T08:00:00") == "2026-06-14"


def test_ts_to_date_empty() -> None:
    from easy_tdx.cninfo.client import _ts_to_date

    assert _ts_to_date("") == ""
    assert _ts_to_date(None) == ""


# ---------------------------------------------------------------------------
# orgId 解析（动态表 + 三段 fallback）
# ---------------------------------------------------------------------------


@pytest.fixture
def reset_orgid_cache() -> Any:
    """每个测试前后清空 orgId 缓存，保证隔离。"""
    import easy_tdx.cninfo.client as mod

    mod._ORGID_MAP.clear()
    yield
    mod._ORGID_MAP.clear()


def _patch_stock_map(monkeypatch: pytest.MonkeyPatch, mapping: dict[str, str]) -> None:
    """让 _fetch_stock_map 返回给定映射（不触网）。"""
    monkeypatch.setattr(
        "easy_tdx.cninfo.client._http_get_json",
        lambda url, timeout=15.0: {
            "stockList": [{"code": c, "orgId": o} for c, o in mapping.items()]
        },
    )


def test_resolve_orgid_from_dynamic_map(
    monkeypatch: pytest.MonkeyPatch, reset_orgid_cache: Any
) -> None:
    """动态表命中应返回表中 orgId。"""
    from easy_tdx.cninfo import CninfoClient

    _patch_stock_map(monkeypatch, {"688017": "9900041602", "601318": "9900002221"})
    client = CninfoClient()
    assert client._resolve_orgid("688017") == "9900041602"
    assert client._resolve_orgid("601318") == "9900002221"


def test_resolve_orgid_fallback_6_prefix(
    monkeypatch: pytest.MonkeyPatch, reset_orgid_cache: Any
) -> None:
    """动态表无此 code 且 6 开头 → gssh0{code}。"""
    from easy_tdx.cninfo import CninfoClient

    _patch_stock_map(monkeypatch, {})
    client = CninfoClient()
    assert client._resolve_orgid("600519") == "gssh0600519"


def test_resolve_orgid_fallback_8_prefix(
    monkeypatch: pytest.MonkeyPatch, reset_orgid_cache: Any
) -> None:
    """北交所 8/4 开头 → gsbj0{code}。"""
    from easy_tdx.cninfo import CninfoClient

    _patch_stock_map(monkeypatch, {})
    client = CninfoClient()
    assert client._resolve_orgid("830799") == "gsbj0830799"
    assert client._resolve_orgid("430047") == "gsbj0430047"


def test_resolve_orgid_fallback_sz_default(
    monkeypatch: pytest.MonkeyPatch, reset_orgid_cache: Any
) -> None:
    """其他前缀（深圳）→ gssz0{code}。"""
    from easy_tdx.cninfo import CninfoClient

    _patch_stock_map(monkeypatch, {})
    client = CninfoClient()
    assert client._resolve_orgid("000001") == "gssz0000001"


def test_resolve_orgid_empty_map_does_not_cache(
    monkeypatch: pytest.MonkeyPatch, reset_orgid_cache: Any
) -> None:
    """映射表为空时不写入缓存，下次仍会重试（避免永久 fallback）。"""
    import easy_tdx.cninfo.client as mod
    from easy_tdx.cninfo import CninfoClient

    _patch_stock_map(monkeypatch, {})
    client = CninfoClient()
    client._resolve_orgid("600519")
    assert mod._ORGID_MAP == {}


def test_resolve_orgid_fetch_failure_fallback(
    monkeypatch: pytest.MonkeyPatch, reset_orgid_cache: Any
) -> None:
    """映射表拉取异常应 graceful fallback 到硬编码规则，不抛错。"""
    from easy_tdx.cninfo import CninfoClient

    def _boom(url: str, timeout: float = 15.0) -> Any:
        raise OSError("network down")

    monkeypatch.setattr("easy_tdx.cninfo.client._http_get_json", _boom)
    client = CninfoClient()
    # 不抛错，回退 SH 规则
    assert client._resolve_orgid("600519") == "gssh0600519"


def test_resolve_orgid_cache_reused(
    monkeypatch: pytest.MonkeyPatch, reset_orgid_cache: Any
) -> None:
    """第二次调用不应再次拉取映射表（缓存命中）。"""
    call_count = {"n": 0}

    def _fake(url: str, timeout: float = 15.0) -> Any:
        call_count["n"] += 1
        return {"stockList": [{"code": "688017", "orgId": "9900041602"}]}

    monkeypatch.setattr("easy_tdx.cninfo.client._http_get_json", _fake)
    from easy_tdx.cninfo import CninfoClient

    client = CninfoClient()
    client._resolve_orgid("688017")
    client._resolve_orgid("688017")
    assert call_count["n"] == 1


# ---------------------------------------------------------------------------
# 公告查询与解析
# ---------------------------------------------------------------------------


_QUERY_RESPONSE: dict[str, Any] = {
    "announcements": [
        {
            "announcementTitle": "关于召开2025年年度股东大会的通知",
            "announcementTypeName": "股东大会",
            "announcementTime": 1749859200000,
            "announcementId": "abc123",
        },
        {
            "announcementTitle": "2024年年度报告",
            "announcementTypeName": "定期报告",
            "announcementTime": 1740614400000,
            "announcementId": "def456",
        },
    ],
    "totalAnnouncement": 2,
}


def test_get_announcements_returns_dataframe(
    monkeypatch: pytest.MonkeyPatch, reset_orgid_cache: Any
) -> None:
    """应返回 DataFrame[title, type, date, url]。"""
    _patch_stock_map(monkeypatch, {"688017": "9900041602"})
    monkeypatch.setattr(
        "easy_tdx.cninfo.client._http_post_form",
        lambda url, payload, timeout=15.0: _QUERY_RESPONSE,
    )
    from easy_tdx.cninfo import CninfoClient

    df = CninfoClient().get_announcements("688017", count=30, page=1)
    assert isinstance(df, pd.DataFrame)
    assert list(df.columns) == ["title", "type", "date", "url"]
    assert len(df) == 2
    assert df.iloc[0]["title"] == "关于召开2025年年度股东大会的通知"
    assert df.iloc[0]["type"] == "股东大会"
    assert len(df.iloc[0]["date"]) == 10  # YYYY-MM-DD
    assert df.iloc[0]["url"].endswith("abc123")
    assert "cninfo.com.cn" in df.iloc[0]["url"]


def test_get_announcements_empty(monkeypatch: pytest.MonkeyPatch, reset_orgid_cache: Any) -> None:
    """无公告应返回带列名的空 DataFrame。"""
    _patch_stock_map(monkeypatch, {"688017": "9900041602"})
    monkeypatch.setattr(
        "easy_tdx.cninfo.client._http_post_form",
        lambda url, payload, timeout=15.0: {"announcements": []},
    )
    from easy_tdx.cninfo import CninfoClient

    df = CninfoClient().get_announcements("688017")
    assert isinstance(df, pd.DataFrame)
    assert df.empty
    assert list(df.columns) == ["title", "type", "date", "url"]


def test_get_announcements_missing_key(
    monkeypatch: pytest.MonkeyPatch, reset_orgid_cache: Any
) -> None:
    """响应缺少 announcements 键应视为空结果。"""
    _patch_stock_map(monkeypatch, {"688017": "9900041602"})
    monkeypatch.setattr(
        "easy_tdx.cninfo.client._http_post_form",
        lambda url, payload, timeout=15.0: {"totalAnnouncement": 0},
    )
    from easy_tdx.cninfo import CninfoClient

    df = CninfoClient().get_announcements("688017")
    assert df.empty


def test_get_announcements_request_failure_raises_cninfo_error(
    monkeypatch: pytest.MonkeyPatch, reset_orgid_cache: Any
) -> None:
    """HTTP 异常应转为 CninfoError。"""
    _patch_stock_map(monkeypatch, {"688017": "9900041602"})

    def _boom(url: str, payload: dict[str, str], timeout: float = 15.0) -> Any:
        raise OSError("connection refused")

    monkeypatch.setattr("easy_tdx.cninfo.client._http_post_form", _boom)
    from easy_tdx.cninfo import CninfoClient, CninfoError

    with pytest.raises(CninfoError):
        CninfoClient().get_announcements("688017")


def test_get_announcements_pagination(
    monkeypatch: pytest.MonkeyPatch, reset_orgid_cache: Any
) -> None:
    """count/page 应正确传入 payload。"""
    _patch_stock_map(monkeypatch, {"688017": "9900041602"})
    captured: dict[str, Any] = {}

    def _capture(url: str, payload: dict[str, str], timeout: float = 15.0) -> Any:
        captured.update(payload)
        return {"announcements": []}

    monkeypatch.setattr("easy_tdx.cninfo.client._http_post_form", _capture)
    from easy_tdx.cninfo import CninfoClient

    CninfoClient().get_announcements("688017", count=50, page=3)
    assert captured["pageSize"] == "50"
    assert captured["pageNum"] == "3"
    assert captured["stock"] == "688017,9900041602"
    assert captured["tabName"] == "fulltext"


def test_get_announcements_uses_fallback_orgid(
    monkeypatch: pytest.MonkeyPatch, reset_orgid_cache: Any
) -> None:
    """601xxx 段动态表未命中时用 gssh0 fallback，stock 字段含该 orgId。"""
    _patch_stock_map(monkeypatch, {})  # 空表 → fallback
    captured: dict[str, Any] = {}

    def _capture(url: str, payload: dict[str, str], timeout: float = 15.0) -> Any:
        captured.update(payload)
        return {"announcements": []}

    monkeypatch.setattr("easy_tdx.cninfo.client._http_post_form", _capture)
    from easy_tdx.cninfo import CninfoClient

    CninfoClient().get_announcements("601318")
    assert captured["stock"] == "601318,gssh0601318"


def test_get_announcements_skips_non_dict_items(
    monkeypatch: pytest.MonkeyPatch, reset_orgid_cache: Any
) -> None:
    """announcements 列表中混入非 dict 元素应被跳过。"""
    _patch_stock_map(monkeypatch, {"688017": "9900041602"})
    monkeypatch.setattr(
        "easy_tdx.cninfo.client._http_post_form",
        lambda url, payload, timeout=15.0: {
            "announcements": [
                "not a dict",
                {
                    "announcementTitle": "ok",
                    "announcementTime": 1749859200000,
                    "announcementId": "x",
                },
            ]
        },
    )
    from easy_tdx.cninfo import CninfoClient

    df = CninfoClient().get_announcements("688017")
    assert len(df) == 1
    assert df.iloc[0]["title"] == "ok"


def test_get_announcements_response_not_dict(
    monkeypatch: pytest.MonkeyPatch, reset_orgid_cache: Any
) -> None:
    """响应非 dict（如 list）应视为空结果，不抛错。"""
    _patch_stock_map(monkeypatch, {"688017": "9900041602"})
    monkeypatch.setattr(
        "easy_tdx.cninfo.client._http_post_form",
        lambda url, payload, timeout=15.0: ["unexpected", "list"],
    )
    from easy_tdx.cninfo import CninfoClient

    df = CninfoClient().get_announcements("688017")
    assert df.empty


def test_get_announcements_malformed_timestamp_wrapped_as_cninfo_error(
    monkeypatch: pytest.MonkeyPatch, reset_orgid_cache: Any
) -> None:
    """announcementTime 畸形（导致 fromtimestamp 溢出）应转 CninfoError，不裸抛。

    回归 #2：修复前 _ts_to_date 在 try 块外，畸形时间戳会抛 OverflowError/
    ValueError 裸异常；修复后整个解析路径统一转 CninfoError。
    """
    _patch_stock_map(monkeypatch, {"688017": "9900041602"})
    monkeypatch.setattr(
        "easy_tdx.cninfo.client._http_post_form",
        lambda url, payload, timeout=15.0: {
            "announcements": [
                {"announcementTitle": "x", "announcementTime": 10**30, "announcementId": "y"}
            ]
        },
    )
    from easy_tdx.cninfo import CninfoClient, CninfoError

    with pytest.raises(CninfoError):
        CninfoClient().get_announcements("688017")


# ---------------------------------------------------------------------------
# urllib helper 烟雾测试（不触网，仅验证 JSON 解码路径）
# ---------------------------------------------------------------------------


def test_http_post_form_urlencoded_body(monkeypatch: pytest.MonkeyPatch) -> None:
    """_http_post_form 应以 application/x-www-form-urlencoded 发送。"""
    import easy_tdx.cninfo.client as mod

    captured: dict[str, Any] = {}

    class _FakeResp:
        def __init__(self, body: bytes) -> None:
            self._body = body

        def read(self) -> bytes:
            return self._body

        def __enter__(self) -> _FakeResp:
            return self

        def __exit__(self, *args: Any) -> None:
            pass

    def _fake_urlopen(req: Any, timeout: float = 15.0) -> _FakeResp:
        captured["data"] = req.data
        captured["headers"] = {k: v for k, v in req.header_items()}
        captured["method"] = req.get_method()
        return _FakeResp(json.dumps({"ok": True}).encode("utf-8"))

    monkeypatch.setattr(mod.urlrequest, "urlopen", _fake_urlopen)
    result = mod._http_post_form("https://example.com/api", {"pageNum": "2", "pageSize": "30"})
    assert result == {"ok": True}
    assert b"pageNum=2" in captured["data"]
    assert b"pageSize=30" in captured["data"]
    assert captured["method"] == "POST"
    headers = {k.lower(): v for k, v in captured["headers"].items()}
    assert "cninfo.com.cn" in headers.get("referer", "")
    assert "x-www-form-urlencoded" in headers.get("content-type", "")


def test_http_get_json_headers(monkeypatch: pytest.MonkeyPatch) -> None:
    """_http_get_json 应携带 User-Agent。"""
    import easy_tdx.cninfo.client as mod

    captured: dict[str, Any] = {}

    class _FakeResp:
        def read(self) -> bytes:
            return json.dumps({"ok": 1}).encode("utf-8")

        def __enter__(self) -> _FakeResp:
            return self

        def __exit__(self, *args: Any) -> None:
            pass

    def _fake_urlopen(req: Any, timeout: float = 15.0) -> _FakeResp:
        captured["headers"] = {k: v for k, v in req.header_items()}
        return _FakeResp()

    monkeypatch.setattr(mod.urlrequest, "urlopen", _fake_urlopen)
    assert mod._http_get_json("https://example.com/x.json") == {"ok": 1}
    headers = {k.lower(): v for k, v in captured["headers"].items()}
    assert "user-agent" in headers
