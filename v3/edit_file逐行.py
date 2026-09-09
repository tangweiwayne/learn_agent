"""edit_file() 逐行跟踪 —— 每执行一行就打印变量的值。

运行： python3 edit_file逐行.py
"""

import os
import tempfile


def 打印(标签, 值):
    print(f"     {标签:12s} = {值!r}")


# ── 准备一个测试文件 ────────────────────────────────
目录 = tempfile.mkdtemp(prefix="trace_")
with open(os.path.join(目录, "demo.py"), "w", encoding="utf-8") as f:
    f.write("def div(a, b):\n    return a / b\n\nprint(div(10, 2))\n")

# ── 模型传来的参数 ──────────────────────────────────
path = "demo.py"
old = "    return a / b"
new = '    if b == 0:\n        raise ValueError("除数不能为0")\n    return a / b'
cwd = 目录

print("=" * 70)
print("  进函数时，手上有这四个值")
print("=" * 70)
for 名, 值 in [("path", path), ("old", old), ("new", new), ("cwd", cwd)]:
    打印(名, 值)


# ── 第 93 行 ────────────────────────────────────────
print("\n" + "=" * 70)
print("  第 93 行：全路径 = os.path.join(cwd or os.getcwd(), path)")
print("=" * 70)
全路径 = os.path.join(cwd or os.getcwd(), path)
打印("cwd or ...", cwd or os.getcwd())
打印("全路径", 全路径)


# ── 第 95 行 ────────────────────────────────────────
print("\n" + "=" * 70)
print("  第 95 行：if not os.path.exists(全路径)")
print("=" * 70)
存在 = os.path.exists(全路径)
打印("exists", 存在)
打印("not exists", not 存在)
print(f"     -> {'返回错误，函数结束' if not 存在 else '文件在，继续往下'}")


# ── 第 99-100 行 ────────────────────────────────────
print("\n" + "=" * 70)
print("  第 99-100 行：读文件")
print("=" * 70)
with open(全路径, encoding="utf-8") as f:
    内容 = f.read()
打印("内容", 内容)
print("\n     渲染出来：")
for i, l in enumerate(内容.splitlines(), 1):
    print(f"        {i}| {l}")


# ── 第 102 行 ───────────────────────────────────────
print("\n" + "=" * 70)
print("  第 102 行：次数 = 内容.count(old)   ← 核心")
print("=" * 70)
次数 = 内容.count(old)
打印("old", old)
打印("次数", 次数)
print(f"     -> {'0 次：报错' if 次数 == 0 else ('1 次：可以改 ✅' if 次数 == 1 else f'{次数} 次：报错')}")


# ── 第 114 行 ───────────────────────────────────────
print("\n" + "=" * 70)
print("  第 114 行：新内容 = 内容.replace(old, new, 1)")
print("=" * 70)
新内容 = 内容.replace(old, new, 1)
打印("内容(旧)", 内容)
打印("新内容", 新内容)
print("     ^ 注意 内容 本身没变 —— 字符串不可变，replace 返回新的")


# ── 第 115-116 行 ───────────────────────────────────
print("\n" + "=" * 70)
print('  第 115-116 行：open(全路径, "w") 写回去')
print("=" * 70)
with open(全路径, "w", encoding="utf-8") as f:
    f.write(新内容)
print("     写完了。文件现在是：")
for i, l in enumerate(open(全路径, encoding="utf-8").read().splitlines(), 1):
    print(f"        {i}| {l}")


# ── 第 119 行 ───────────────────────────────────────
print("\n" + "=" * 70)
print('  第 119 行：行号 = 内容[: 内容.index(old)].count("\\n") + 1')
print("=" * 70)
位置 = 内容.index(old)
打印("index(old)", 位置)
前面 = 内容[:位置]
打印("内容[:位置]", 前面)
换行数 = 前面.count("\n")
打印('count("\\n")', 换行数)
行号 = 换行数 + 1
打印("行号(+1)", 行号)


# ── 第 120-122 行 ───────────────────────────────────
print("\n" + "=" * 70)
print("  第 120-122 行：返回给模型的文字")
print("=" * 70)
结果 = (f"<success>已修改 {path}（第 {行号} 行附近）</success>\n"
        f"<removed>\n{old}\n</removed>\n"
        f"<added>\n{new}\n</added>")
print()
for l in 结果.splitlines():
    print("     " + l)

print(f"\n  （测试文件在 {目录}，看完可以删）")
