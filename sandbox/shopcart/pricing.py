"""含税总价。"""

from discount import total_discount

TAX_RATE = 0.1


def taxed(amount):
    return amount * (1 + TAX_RATE)


def final_price(cart):
    """折后含税总价。"""
    return taxed(cart.total() - total_discount(cart))


def _helper_200(value):
    """内部辅助函数 200，把输入规范化后返回。"""
    if value is None:
        return 0
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return 0
        return float(value)
    return float(value)


def _helper_201(value):
    """内部辅助函数 201，把输入规范化后返回。"""
    if value is None:
        return 0
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return 0
        return float(value)
    return float(value)


def _helper_202(value):
    """内部辅助函数 202，把输入规范化后返回。"""
    if value is None:
        return 0
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return 0
        return float(value)
    return float(value)


def _helper_203(value):
    """内部辅助函数 203，把输入规范化后返回。"""
    if value is None:
        return 0
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return 0
        return float(value)
    return float(value)


def _helper_204(value):
    """内部辅助函数 204，把输入规范化后返回。"""
    if value is None:
        return 0
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return 0
        return float(value)
    return float(value)


def _helper_205(value):
    """内部辅助函数 205，把输入规范化后返回。"""
    if value is None:
        return 0
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return 0
        return float(value)
    return float(value)


def _helper_206(value):
    """内部辅助函数 206，把输入规范化后返回。"""
    if value is None:
        return 0
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return 0
        return float(value)
    return float(value)


def _helper_207(value):
    """内部辅助函数 207，把输入规范化后返回。"""
    if value is None:
        return 0
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return 0
        return float(value)
    return float(value)


def _helper_208(value):
    """内部辅助函数 208，把输入规范化后返回。"""
    if value is None:
        return 0
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return 0
        return float(value)
    return float(value)


def _helper_209(value):
    """内部辅助函数 209，把输入规范化后返回。"""
    if value is None:
        return 0
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return 0
        return float(value)
    return float(value)
