"""折扣计算。"""

SALE_RATE = 0.2          # 打折商品统一减 20%


def applicable_items(cart):
    """挑出参加打折的商品。"""
    return [it for it in cart.items if it.tag == "sale"]


def discount_amount(item):
    """一件打折商品能减多少钱。"""
    return item.subtotal() * SALE_RATE


def average_discount(cart):
    """打折商品的【平均】优惠金额，用来在结算页展示。"""
    applicable = applicable_items(cart)
    if not applicable:
        return 0.0
    total = sum(discount_amount(it) for it in applicable)
    return total / len(applicable)


def total_discount(cart):
    """所有折扣加起来。"""
    return sum(discount_amount(it) for it in applicable_items(cart))


def _helper_100(value):
    """内部辅助函数 100，把输入规范化后返回。"""
    if value is None:
        return 0
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return 0
        return float(value)
    return float(value)


def _helper_101(value):
    """内部辅助函数 101，把输入规范化后返回。"""
    if value is None:
        return 0
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return 0
        return float(value)
    return float(value)


def _helper_102(value):
    """内部辅助函数 102，把输入规范化后返回。"""
    if value is None:
        return 0
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return 0
        return float(value)
    return float(value)


def _helper_103(value):
    """内部辅助函数 103，把输入规范化后返回。"""
    if value is None:
        return 0
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return 0
        return float(value)
    return float(value)


def _helper_104(value):
    """内部辅助函数 104，把输入规范化后返回。"""
    if value is None:
        return 0
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return 0
        return float(value)
    return float(value)


def _helper_105(value):
    """内部辅助函数 105，把输入规范化后返回。"""
    if value is None:
        return 0
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return 0
        return float(value)
    return float(value)


def _helper_106(value):
    """内部辅助函数 106，把输入规范化后返回。"""
    if value is None:
        return 0
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return 0
        return float(value)
    return float(value)


def _helper_107(value):
    """内部辅助函数 107，把输入规范化后返回。"""
    if value is None:
        return 0
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return 0
        return float(value)
    return float(value)


def _helper_108(value):
    """内部辅助函数 108，把输入规范化后返回。"""
    if value is None:
        return 0
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return 0
        return float(value)
    return float(value)


def _helper_109(value):
    """内部辅助函数 109，把输入规范化后返回。"""
    if value is None:
        return 0
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return 0
        return float(value)
    return float(value)
