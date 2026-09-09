"""入口：跑两个购物车。"""

from models import Cart, Item
from report import render


def demo_with_sale():
    cart = Cart([
        Item("鼠标", 99, 2, tag="sale"),
        Item("键盘", 299, 1, tag="sale"),
        Item("显示器", 1299, 1),
    ])
    print(render(cart))


def demo_no_sale():
    cart = Cart([
        Item("水杯", 39, 1),
        Item("笔记本", 12, 3),
    ])
    print(render(cart))


if __name__ == "__main__":
    demo_with_sale()
    print()
    demo_no_sale()
