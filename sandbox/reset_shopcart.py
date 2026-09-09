"""重建 shopcart 靶场到【有 bug】的原始状态。每次做实验前先跑它。

跑法：  python3 reset_shopcart.py
"""
import os
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
DIR = os.path.join(HERE, "shopcart")

FILLER = '''

def _helper_{n}(value):
    """内部辅助函数 {n}，把输入规范化后返回。"""
    if value is None:
        return 0
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return 0
        return float(value)
    return float(value)
'''


def pad(base, k, start=1):
    return base + "".join(FILLER.format(n=i) for i in range(start, start + k))


FILES = {}

FILES["models.py"] = pad('''"""商品和购物车的数据结构。"""


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
''', 12)

FILES["discount.py"] = pad('''"""折扣计算。"""

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
    total = sum(discount_amount(it) for it in applicable)
    return total / len(applicable)


def total_discount(cart):
    """所有折扣加起来。"""
    return sum(discount_amount(it) for it in applicable_items(cart))
''', 10, start=100)

FILES["pricing.py"] = pad('''"""含税总价。"""

from discount import total_discount

TAX_RATE = 0.1


def taxed(amount):
    return amount * (1 + TAX_RATE)


def final_price(cart):
    """折后含税总价。"""
    return taxed(cart.total() - total_discount(cart))
''', 10, start=200)

FILES["report.py"] = pad('''"""把购物车打印成一张小票。"""

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
    return "\\n".join(lines)
''', 10, start=300)

FILES["main.py"] = '''"""入口：跑两个购物车。"""

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
'''

os.makedirs(DIR, exist_ok=True)
cache = os.path.join(DIR, "__pycache__")
if os.path.isdir(cache):
    try:
        shutil.rmtree(cache)      # 不清缓存的话 .pyc 可能还是旧的
    except OSError as e:
        print(f"（清 __pycache__ 失败，可忽略：{e}）")

for name, content in FILES.items():
    with open(os.path.join(DIR, name), "w", encoding="utf-8") as f:
        f.write(content)

print(f"已重建 {DIR}（{len(FILES)} 个文件，bug 已还原）")
print("验证：")
os.system(f'cd "{DIR}" && python3 main.py 2>&1 | tail -3')
