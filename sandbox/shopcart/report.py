"""把购物车打印成一张小票。"""

from discount import average_discount, total_discount
from pricing import final_price


def render(cart):
    lines = ["===== 小票 ====="]
    for it in cart.items:
        lines.append(f"{it.name:<10} x{it.qty:<3} {it.subtotal():>8.2f}")
    lines.append("-" * 16)
    lines.append(f"{'小计':<14}{cart.total():>8.2f}")
    lines.append(f"{'折扣':<14}{total_discount(cart):>8.2f}")
    lines.append(f"{'平均折扣':<12}{average_discount(cart):>8.2f}")
    lines.append(f"{'应付':<14}{final_price(cart):>8.2f}")
    return "\n".join(lines)


def _helper_300(value):
    """内部辅助函数 300，把输入规范化后返回。"""
    if value is None:
        return 0
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return 0
        return float(value)
    return float(value)


def _helper_301(value):
    """内部辅助函数 301，把输入规范化后返回。"""
    if value is None:
        return 0
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return 0
        return float(value)
    return float(value)


def _helper_302(value):
    """内部辅助函数 302，把输入规范化后返回。"""
    if value is None:
        return 0
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return 0
        return float(value)
    return float(value)


def _helper_303(value):
    """内部辅助函数 303，把输入规范化后返回。"""
    if value is None:
        return 0
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return 0
        return float(value)
    return float(value)


def _helper_304(value):
    """内部辅助函数 304，把输入规范化后返回。"""
    if value is None:
        return 0
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return 0
        return float(value)
    return float(value)


def _helper_305(value):
    """内部辅助函数 305，把输入规范化后返回。"""
    if value is None:
        return 0
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return 0
        return float(value)
    return float(value)


def _helper_306(value):
    """内部辅助函数 306，把输入规范化后返回。"""
    if value is None:
        return 0
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return 0
        return float(value)
    return float(value)


def _helper_307(value):
    """内部辅助函数 307，把输入规范化后返回。"""
    if value is None:
        return 0
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return 0
        return float(value)
    return float(value)


def _helper_308(value):
    """内部辅助函数 308，把输入规范化后返回。"""
    if value is None:
        return 0
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return 0
        return float(value)
    return float(value)


def _helper_309(value):
    """内部辅助函数 309，把输入规范化后返回。"""
    if value is None:
        return 0
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return 0
        return float(value)
    return float(value)
