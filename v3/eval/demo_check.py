"""看 check_fixed 的三道关分别是怎么响的。

跑法：  python3 demo_check.py      （不联网、不花钱、不动你的文件）
"""
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fixtures
from tasks import check_fixed

FIX_OLD = "    total = sum(it.subtotal() * SALE_RATE for it in applicable)"
FIX_NEW = ("    if not applicable:\n        return 0.0\n"
           "    total = sum(it.subtotal() * SALE_RATE for it in applicable)")


class StubAgent:
    """check_fixed 不看 agent，随便给一个占位对象就行。"""
    messages = []
    step_count = 0


def fix_properly(workdir):
    """正确的修法：加两行判空。"""
    path = os.path.join(workdir, "discount.py")
    with open(path) as f:
        content = f.read()
    with open(path, "w") as f:
        f.write(content.replace(FIX_OLD, FIX_NEW))


def do_nothing(workdir):
    pass


def cheat_delete_print(workdir):
    """作弊：修是修了，但把那行打印删了 —— 退出码也是 0。"""
    fix_properly(workdir)
    path = os.path.join(workdir, "main.py")
    with open(path) as f:
        kept = [ln for ln in f.read().splitlines() if "平均折扣" not in ln]
    with open(path, "w") as f:
        f.write("\n".join(kept))


def fix_but_touch_models(workdir):
    """修对了，但顺手动了任务没让动的文件。"""
    fix_properly(workdir)
    with open(os.path.join(workdir, "models.py"), "a") as f:
        f.write("\n\n# 顺手加个注释\n")


CASES = [
    ("① 什么都没修", do_nothing),
    ("② 正确地修好了", fix_properly),
    ("③ 修了，但删掉了那行打印（作弊）", cheat_delete_print),
    ("④ 修了，但顺手动了 models.py", fix_but_touch_models),
]

print("check_fixed 在四种情况下的判定：\n")
for title, mutate in CASES:
    workdir = tempfile.mkdtemp(prefix="demo_check_")
    try:
        state = fixtures.setup_buggy(workdir)     # 每次都从同一个起点开始
        mutate(workdir)
        ok, why = check_fixed(workdir, StubAgent(), state)
        print(f"  {'✅PASS' if ok else '❌FAIL'}  {title:<34} → {why}")
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
