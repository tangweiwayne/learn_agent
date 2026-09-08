"""
正则替换练习 —— 直接运行： python3 练习_正则.py
一步一步，每步都打印结果。看懂了就去改改看会怎样。
"""

import re

print("=" * 60)
print("【1】m 是什么：一个'档案袋'，不是字符串")
print("=" * 60)
m = re.search(r"\d+", "我今年18岁")
print("  re.search(r'\\d+', '我今年18岁')")
print("  →", m)
print("  m.group(0) →", repr(m.group(0)), "  ← 用 group 才能掏出内容")


print()
print("=" * 60)
print("【2】括号 = 这一段我要单独拿")
print("=" * 60)
m = re.search(r"(\w+):(\d+)", "张三:18")
print("  正则:  (\\w+)  :  (\\d+)")
print("         └第1对┘    └第2对┘")
print("  文本:   张三   :   18")
print()
print("  m.group(0) →", repr(m.group(0)), "  整个匹配")
print("  m.group(1) →", repr(m.group(1)), "     第1对括号")
print("  m.group(2) →", repr(m.group(2)), "       第2对括号")


print()
print("=" * 60)
print("【3】re.sub = 查找并替换（换成固定字符串）")
print("=" * 60)
print("  re.sub(r'\\d+', 'X', 'a1b22c333')")
print("  →", repr(re.sub(r"\d+", "X", "a1b22c333")))


print()
print("=" * 60)
print("【4】把'换成什么'改成一个函数")
print("=" * 60)
print("  需求：每个数字翻倍。固定字符串做不到，因为它不会算数。")
print()

def 翻倍(m):
    原来的 = m.group(0)
    新的 = str(int(原来的) * 2)
    print(f"    [函数被调用] 掏出 {原来的!r} → 返回 {新的!r}")
    return 新的

结果 = re.sub(r"\d+", 翻倍, "a1b22c333")
print("  →", repr(结果))
print()
print("  ★ 有几处匹配，函数就被调用几次")
print("  ★ 每次把那一处的档案袋 m 递给你")
print("  ★ 你 return 什么，就替换成什么")


print()
print("=" * 60)
print("【5】同样的套路，做模板填空")
print("=" * 60)
表 = {"name": "小明", "age": 18}
print("  变量表 =", 表)
print()

def 填空(m):
    名字 = m.group(1)
    值 = 表[名字]
    print(f"    [函数被调用] group(0)={m.group(0)!r}  group(1)={名字!r}  查表得 {值!r}")
    return str(值)

结果 = re.sub(r"\{\{(\w+)\}\}", 填空, "你好{{name}}，{{age}}岁")
print("  →", repr(结果))
print()
print("  ★ 为什么这里用 group(1) 而不是 group(0)？")
print("    因为 '{{name}}' 整个都要被换掉，")
print("    但只有 'name' 这四个字母是查表的钥匙。")


print()
print("=" * 60)
print("【6】两个函数并排看，是同一个骨架")
print("=" * 60)
print("""
     def 翻倍(m):                    def 填空(m):
         x = m.group(0)                  x = m.group(1)
         return str(int(x) * 2)          return str(表[x])

     唯一差别：用 group(0) 还是 group(1)
""")


print("=" * 60)
print("【7】{% if %}：需要两块信息，所以两对括号")
print("=" * 60)
模板 = "开头{% if 显示 %}[中间这段]{% endif %}结尾"
print("  模板:", repr(模板))
print()
print("  正则:  {% if  (\\w+)  %}  (.*?)  {% endif %}")
print("                └第1对┘     └第2对┘")

def 处理if(变量表):
    def _f(m):
        名字, 内容 = m.group(1), m.group(2)
        留不留 = 变量表.get(名字)
        print(f"    [函数被调用] group(1)={名字!r} group(2)={内容!r} "
              f"→ 值是 {留不留}，{'保留内容' if 留不留 else '整段删掉'}")
        return 内容 if 留不留 else ""
    return _f

正则if = r"\{%\s*if\s+(\w+)\s*%\}(.*?)\{%\s*endif\s*%\}"

print()
print("  ▼ 当 显示=True")
print("  →", repr(re.sub(正则if, 处理if({"显示": True}), 模板, flags=re.DOTALL)))
print()
print("  ▼ 当 显示=False（同一个模板！）")
print("  →", repr(re.sub(正则if, 处理if({"显示": False}), 模板, flags=re.DOTALL)))


print()
print("=" * 60)
print("【8】自己改改看")
print("=" * 60)
print("""  打开这个文件，试试：
    · 把【4】的 *2 改成 *10
    · 把【5】的 表 加一项 "city": "东京"，
      再把文本改成 "你好{{name}}，{{age}}岁，住在{{city}}"
    · 把【7】的 显示 改来改去
  改完存盘，重新运行，看结果怎么变。
""")
