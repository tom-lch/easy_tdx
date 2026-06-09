"""easy_tdx.screen — 策略选股扫描器。

两步走工作流：
1. scan: 用策略扫描全市场，找出触发买入信号的股票（纯离线）
2. rank: 对扫描结果做历史回测排名

用法::

    # Step 1: 信号扫描
    easy-tdx screen scan --strategy strategies/rsi_reversal.py --output signals.json

    # Step 2: 回测排名
    easy-tdx screen rank --from signals.json --sort sharpe --top 20 --table
"""

from easy_tdx.screen.scanner import ScanResult, SignalScanner  # noqa: F401

__all__ = [
    "SignalScanner",
    "ScanResult",
]
