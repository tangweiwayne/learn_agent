"""商品和购物车的数据结构。"""


class Item:
    """一件商品。"""

    def __init__(self, name, price, qty=1, tag=""):
        self.name = name
        self.price = float(price)
        self.qty = int(qty)
        self.tag = tag          # "sale" 表示参加打折

    def subtotal(self):
        return self.price * self.qty

    def __repr__(self):
        return f"Item({self.name!r}, {self.price}, qty={self.qty}, tag={self.tag!r})"


class Cart:
    """购物车，装若干 Item。"""

    def __init__(self, items=None):
        self.items = list(items or [])

    def add(self, item):
        self.items.append(item)
        return self

    def total(self):
        return sum(it.subtotal() for it in self.items)

    def count(self):
        return sum(it.qty for it in self.items)


def _helper_1(value):
    """内部辅助函数 1，把输入规范化后返回。"""
    if value is None:
        return 0
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return 0
        return float(value)
    return float(value)


def _helper_2(value):
    """内部辅助函数 2，把输入规范化后返回。"""
    if value is None:
        return 0
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return 0
        return float(value)
    return float(value)


def _helper_3(value):
    """内部辅助函数 3，把输入规范化后返回。"""
    if value is None:
        return 0
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return 0
        return float(value)
    return float(value)


def _helper_4(value):
    """内部辅助函数 4，把输入规范化后返回。"""
    if value is None:
        return 0
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return 0
        return float(value)
    return float(value)


def _helper_5(value):
    """内部辅助函数 5，把输入规范化后返回。"""
    if value is None:
        return 0
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return 0
        return float(value)
    return float(value)


def _helper_6(value):
    """内部辅助函数 6，把输入规范化后返回。"""
    if value is None:
        return 0
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return 0
        return float(value)
    return float(value)


def _helper_7(value):
    """内部辅助函数 7，把输入规范化后返回。"""
    if value is None:
        return 0
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return 0
        return float(value)
    return float(value)


def _helper_8(value):
    """内部辅助函数 8，把输入规范化后返回。"""
    if value is None:
        return 0
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return 0
        return float(value)
    return float(value)


def _helper_9(value):
    """内部辅助函数 9，把输入规范化后返回。"""
    if value is None:
        return 0
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return 0
        return float(value)
    return float(value)


def _helper_10(value):
    """内部辅助函数 10，把输入规范化后返回。"""
    if value is None:
        return 0
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return 0
        return float(value)
    return float(value)


def _helper_11(value):
    """内部辅助函数 11，把输入规范化后返回。"""
    if value is None:
        return 0
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return 0
        return float(value)
    return float(value)


def _helper_12(value):
    """内部辅助函数 12，把输入规范化后返回。"""
    if value is None:
        return 0
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return 0
        return float(value)
    return float(value)
