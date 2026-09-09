"""基本的四则运算模块。"""


def add(a, b):
    """返回 a + b。"""
    return a + b


def sub(a, b):
    """返回 a - b。"""
    return a - b


def mul(a, b):
    """返回 a * b。"""
    return a * b


def div(a, b):
    """返回 a / b；除数为 0 时抛出 ValueError。"""
    if b == 0:
        raise ValueError("除数不能为 0（division by zero）")
    return a / b
