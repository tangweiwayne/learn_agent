"""靶场：每个 eval 任务开跑前，用这里的函数把目录铺成已知状态。

刻意做得很小（3 个文件、几十行），因为 eval 要反复跑，靶场越大越贵。
"""
import hashlib
import os

MODELS = '''"""商品和购物车。"""


class Item:
    def __init__(self, name, price, qty=1, tag=""):
        self.name = name
        self.price = float(price)
        self.qty = int(qty)
        self.tag = tag          # "sale" 表示参加打折

    def subtotal(self):
        return self.price * self.qty


class Cart:
    def __init__(self, items=None):
        self.items = list(items or [])

    def total(self):
        return sum(it.subtotal() for it in self.items)
'''

DISCOUNT_BUGGY = '''"""折扣计算。"""

SALE_RATE = 0.2


def applicable_items(cart):
    return [it for it in cart.items if it.tag == "sale"]


def average_discount(cart):
    """打折商品的平均优惠金额。"""
    applicable = applicable_items(cart)
    total = sum(it.subtotal() * SALE_RATE for it in applicable)
    return total / len(applicable)


def total_discount(cart):
    return sum(it.subtotal() * SALE_RATE for it in applicable_items(cart))
'''

# 唯一的差别：多了两行判空
DISCOUNT_OK = DISCOUNT_BUGGY.replace(
    "    total = sum(it.subtotal() * SALE_RATE for it in applicable)",
    "    if not applicable:\n"
    "        return 0.0\n"
    "    total = sum(it.subtotal() * SALE_RATE for it in applicable)",
)

MAIN = '''"""入口：跑两个购物车。"""

from models import Cart, Item
from discount import average_discount, total_discount


def show(cart, title):
    print(f"--- {title} ---")
    print(f"小计     {cart.total():.2f}")
    print(f"折扣     {total_discount(cart):.2f}")
    print(f"平均折扣 {average_discount(cart):.2f}")


if __name__ == "__main__":
    show(Cart([Item("鼠标", 99, 2, tag="sale"), Item("显示器", 1299, 1)]), "有打折商品")
    print()
    show(Cart([Item("水杯", 39, 1), Item("笔记本", 12, 3)]), "没有打折商品")
'''


def _write(workdir: str, files: dict) -> dict:
    """把 files 写进 workdir，返回 {文件名: 内容的 md5}，给 check 做"有没有被动过"的对照。"""
    os.makedirs(workdir, exist_ok=True)
    fingerprints = {}
    for name, content in files.items():
        with open(os.path.join(workdir, name), "w", encoding="utf-8") as f:
            f.write(content)
        fingerprints[name] = hashlib.md5(content.encode("utf-8")).hexdigest()
    return fingerprints


def setup_buggy(workdir: str) -> dict:
    """有 bug 的版本：没有打折商品时 average_discount 会除零。"""
    return _write(workdir, {"models.py": MODELS,
                            "discount.py": DISCOUNT_BUGGY,
                            "main.py": MAIN})


def setup_clean(workdir: str) -> dict:
    """已经修好的版本：跑起来完全正常。"""
    return _write(workdir, {"models.py": MODELS,
                            "discount.py": DISCOUNT_OK,
                            "main.py": MAIN})


def md5_of(workdir: str, name: str) -> str:
    path = os.path.join(workdir, name)
    if not os.path.exists(path):
        return "<文件没了>"
    with open(path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()
