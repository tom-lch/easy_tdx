"""因子 CLI 命令。"""
from __future__ import annotations

import json

import click


@click.group("factor")
def factor() -> None:
    """因子研究工具。"""
    pass


@factor.command("list")
@click.option(
    "--category",
    default=None,
    help="按类别筛选: momentum/volatility/quality/volume/technical/chanlun/value",
)
@click.option("--table", "use_table", is_flag=True, help="表格输出")
def factor_list(category: str | None, use_table: bool) -> None:
    """列出所有已注册的因子。

    示例：

      easy-tdx factor list

      easy-tdx factor list --category momentum --table
    """
    from easy_tdx.factor.builtin import list_factors

    factors = list_factors()

    if category:
        factors = [f for f in factors if f["category"] == category]

    if use_table:
        try:
            from tabulate import tabulate

            rows = [
                {
                    "name": f["name"],
                    "category": f["category"],
                    "description": f["description"],
                }
                for f in factors
            ]
            click.echo(tabulate(rows, headers="keys", tablefmt="grid"))
        except ImportError:
            for f in factors:
                click.echo(f"{f['name']}\t{f['category']}\t{f['description']}")
    else:
        click.echo(json.dumps(factors, ensure_ascii=False, indent=2))
