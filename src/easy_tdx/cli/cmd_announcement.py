"""公告检索命令（巨潮资讯网数据源，无需 TDX 服务器）。"""

from __future__ import annotations

import click


@click.command("announcement")
@click.argument("code")
@click.option("--count", default=30, type=int, help="每页数量")
@click.option("--page", default=1, type=int, help="页码（1 起始）")
@click.option("--table", "use_table", is_flag=True, help="表格输出")
@click.option("--output", "output_fmt", type=click.Choice(["json", "table", "csv"]), default="json")
def announcement(code: str, count: int, page: int, use_table: bool, output_fmt: str) -> None:
    """检索公司公告（巨潮资讯网，独立数据源，无需连接 TDX）。

    \b
    示例：

      easy-tdx announcement 688017

      easy-tdx announcement 600519 --count 50 --page 2

      easy-tdx announcement 000001 --table
    """
    from ..cninfo import CninfoClient, CninfoError
    from .output import print_error, print_output

    fmt = "table" if use_table else output_fmt
    client = CninfoClient()
    try:
        df = client.get_announcements(code, count=count, page=page)
    except CninfoError as e:
        print_error(str(e))
        raise SystemExit(1) from e
    print_output(df, fmt)
