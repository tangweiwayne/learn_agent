"""
第三课 · 第二个类：Model

设计要点：
  Model（父类）      —— 管状态：调用次数、累计花费、预算检查
  ├─ DeepSeekModel  —— 只负责：发 HTTP 请求、按 usage 算钱
  └─ MockModel      —— 只负责：念预设台词、花费恒为 0

父类的 query() 是共享骨架，子类只填 _generate() 这个"洞"。
这叫「模板方法模式」。
"""

import json
import os
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))


def _find_env_file() -> str:
    """从本文件所在目录往上找 .env，最多找 3 层。
    这样文件挪到子文件夹里也能找到根目录的 .env。"""
    d = HERE
    for _ in range(3):
        p = os.path.join(d, ".env")
        if os.path.exists(p):
            return p
        d = os.path.dirname(d)
    raise FileNotFoundError("找不到 .env 文件（在本文件往上 3 层目录内都没有）")


def load_env() -> dict:
    """把 .env 里的 KEY=VALUE 读成字典。"""
    env = {}
    with open(_find_env_file(), encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            env[key.strip()] = value.strip().strip("'\"")
    return env


# ==================================================================
# 自定义异常：一个类、一行文档，全部能力从 Exception 继承而来
# ==================================================================
class BudgetExceeded(Exception):
    """累计花费超过了 cost_limit。"""


# ==================================================================
# 父类：只管状态，不管怎么产生文字
# ==================================================================
class Model:
    def __init__(self, cost_limit: float = 0.5):
        self.n_calls = 0            # 状态：调用了几次
        self.total_cost = 0.0       # 状态：累计花了多少美元
        self.cost_limit = cost_limit  # 配置：0 表示不限额

    def query(self, messages: list) -> str:
        """共享骨架：检查预算 → 计数 → 调子类的 _generate → 累加花费。"""
        if 0 < self.cost_limit <= self.total_cost:
            raise BudgetExceeded(
                f"预算用尽：已花 ${self.total_cost:.4f}，上限 ${self.cost_limit:.4f}"
            )
        self.n_calls += 1
        text, cost = self._generate(messages)
        self.total_cost += cost
        return text

    def _generate(self, messages: list):
        """子类必须实现。返回 (回复文字, 这次的花费)。"""
        raise NotImplementedError("子类必须实现 _generate()")

    def stats(self) -> str:
        return f"调用 {self.n_calls} 次，累计 ${self.total_cost:.4f}"


# ==================================================================
# 子类 1：真的调 DeepSeek
# ==================================================================
class DeepSeekModel(Model):
    # 类属性 = 所有实例共享的常量
    # ⚠️ 费率会变！以 https://api-docs.deepseek.com/quick_start/pricing 为准
    PRICE_INPUT = 0.27 / 1_000_000      # 美元 / 每个输入 token
    PRICE_OUTPUT = 1.10 / 1_000_000     # 美元 / 每个输出 token

    def __init__(self, model_name: str = "deepseek-chat", cost_limit: float = 0.5):
        super().__init__(cost_limit=cost_limit)   # ← 先让父类初始化状态
        self.model_name = model_name
        self.env = load_env()

    def _generate(self, messages: list):
        url = self.env["DEEPSEEK_BASE_URL"].rstrip("/") + "/chat/completions"
        payload = json.dumps(
            {   
                "model": self.model_name, 
                "messages": messages
            }
        ).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + self.env["DEEPSEEK_API_KEY"],
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        text = data["choices"][0]["message"]["content"]

        # usage 就是模块3 里我们跳过的那一块，现在用上了
        usage = data.get("usage", {})           # .get 防止 API 不返回它
        n_in = usage.get("prompt_tokens", 0)
        n_out = usage.get("completion_tokens", 0)
        cost = n_in * self.PRICE_INPUT + n_out * self.PRICE_OUTPUT
        return text, cost


# ==================================================================
# 子类 2：假模型，念台词
# ==================================================================
DEFAULT_SCRIPT = [
    "我先看看当前目录里有什么文件。\n\n```bash\nls\n```",
    "有几个文件。现在数一下 .py 文件的数量。\n\n```bash\nls *.py | wc -l\n```",
    "（故意演示一次格式错误：我忘了写代码块）",
    "抱歉，重新发。数完了，任务完成。\n\n```bash\necho TASK_DONE\n```",
]


class MockModel(Model):
    def __init__(self, scripted: list = None, cost_limit: float = 0.0):
        super().__init__(cost_limit=cost_limit)
        self.scripted = scripted or DEFAULT_SCRIPT
        self.i = 0                    # 用实例属性记位置（对比模块7的闭包）

    def _generate(self, messages: list):
        if self.i >= len(self.scripted):
            raise IndexError(f"台词用完了（共 {len(self.scripted)} 句）")
        text = self.scripted[self.i]
        self.i += 1
        return text, 0.0              # 假模型不花钱


# ------------------------------------------------------------------
if __name__ == "__main__":
    print("=== 1. MockModel：状态随调用而变 ===")
    m = MockModel()
    for _ in range(3):
        m.query([])
        print(f"  {m.stats()}   self.i = {m.i}")

    print("\n=== 2. 两个实例互不干扰 ===")
    a, b = MockModel(), MockModel()
    a.query([]); a.query([])
    b.query([])
    print(f"  a: {a.stats()}  i={a.i}")
    print(f"  b: {b.stats()}  i={b.i}")

    print("\n=== 3. 继承：MockModel 没写 query()，但能用 ===")
    print("  MockModel 自己定义的:", [k for k in MockModel.__dict__ if not k.startswith('__')])
    print("  query 其实来自:", MockModel.query.__qualname__)

    print("\n=== 4. 预算熔断 ===")
    class PriceyModel(Model):                 # 临时造一个"每次收 0.1 刀"的模型
        def _generate(self, messages):
            return "假装回复", 0.1

    p = PriceyModel(cost_limit=0.25)
    try:
        for i in range(1, 10):
            p.query([])
            print(f"  第{i}次调用后：{p.stats()}")
    except BudgetExceeded as e:
        print(f"  ⛔ {type(e).__name__}: {e}")

    print("\n=== 5. 忘了实现 _generate 会怎样 ===")
    class Broken(Model):
        pass
    try:
        Broken().query([])
    except NotImplementedError as e:
        print(f"  ⛔ {type(e).__name__}: {e}")

    print("\n=== 6. 台词用完 ===")
    m2 = MockModel(scripted=["只有一句"])
    m2.query([])
    try:
        m2.query([])
    except IndexError as e:
        print(f"  ⛔ {type(e).__name__}: {e}")
