"""Utility functions for stock code handling and formatting."""

import re


def normalize_stock_code(code: str) -> str:
    """Normalize stock code to 6-digit format.

    Handles formats like:
    - "000001" -> "000001"
    - "sh000001" -> "000001"
    - "sz000001" -> "000001"
    - "000001.SZ" -> "000001"
    - "000001.SH" -> "000001"
    - "SH000001" -> "000001"
    - "SZ000001" -> "000001"

    Args:
        code: Stock code in any common format.

    Returns:
        6-digit stock code string.
    """
    code = code.strip().upper()

    # Remove market suffix like .SH, .SZ
    code = re.sub(r'\.(SH|SZ|BJ)$', '', code)

    # Remove market prefix like SH, SZ
    code = re.sub(r'^(SH|SZ|BJ)', '', code)

    # Ensure it's 6 digits, zero-padded
    code = code.zfill(6)

    return code


def get_market_from_code(code: str) -> str:
    """Determine the market (SH/SZ/BJ) from a stock code.

    Rules:
    - 60xxxx, 68xxxx -> SH (Shanghai)
    - 00xxxx, 30xxxx -> SZ (Shenzhen)
    - 4xxxxx, 8xxxxx -> BJ (Beijing/NEEQ)

    Args:
        code: 6-digit stock code.

    Returns:
        Market string: "SH", "SZ", or "BJ".
    """
    code = normalize_stock_code(code)

    if code.startswith('6'):
        return 'SH'
    elif code.startswith(('0', '3')):
        return 'SZ'
    elif code.startswith(('4', '8')):
        return 'BJ'
    else:
        return 'SZ'


def format_number(num, precision: int = 2) -> str:
    """Format a number for display.

    Args:
        num: Number to format (int, float, or None).
        precision: Decimal places to show.

    Returns:
        Formatted string. Returns "--" for None/NaN values.
    """
    if num is None:
        return "--"

    try:
        import math
        if isinstance(num, float) and math.isnan(num):
            return "--"

        num = float(num)

        # Format large numbers with 万/亿 suffixes
        abs_num = abs(num)
        sign = "-" if num < 0 else ""

        if abs_num >= 1e8:
            return f"{sign}{abs_num / 1e8:.{precision}f}亿"
        elif abs_num >= 1e4:
            return f"{sign}{abs_num / 1e4:.{precision}f}万"
        else:
            return f"{num:.{precision}f}"
    except (TypeError, ValueError):
        return str(num)


def get_stock_name_placeholder(code: str) -> str:
    """Get a placeholder name for common indices and stocks.

    Args:
        code: 6-digit stock code.

    Returns:
        Stock/index name, or the code itself if unknown.
    """
    names = {
        '000001': '上证指数',
        '399001': '深证成指',
        '399006': '创业板指',
        '000688': '科创50',
        '000016': '上证50',
        '000300': '沪深300',
        '000905': '中证500',
        '000852': '中证1000',
    }
    return names.get(code, code)
