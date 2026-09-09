"""
v3 · Model：工具call版

和 v2 的差别：
  · 请求里多带一个 tools=[...]，告诉 API 有哪些工具
  · 模型返回的不再是一坨文字，而是结构化的 tool_calls
  · query() 返回【整条 assistant 消息】，不再是字符串

工具的定义在 v3_tools.py 里，这个文件只负责"发请求 + 算钱"。
"""

import json
import os
import urllib.request

from v3_tools import ALL_TOOLS

HERE = os.path.dirname(os.path.abspath(__file__))


def _find_env_file() -> str:
    d = HERE
    for _ in range(3):
        p = os.path.join(d, ".env")
        if os.path.exists(p):
            return p
        d = os.path.dirname(d)
    raise FileNotFoundError("找不到 .env")


def load_env() -> dict:
    env = {}
    with open(_find_env_file(), encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip("'\"")
    return env


class BudgetExceeded(Exception):
    """累计花费超过 cost_limit。"""


# ==================================================================
# 发给 API 之前，只保留 API 认识的字段
# ==================================================================
API_FIELDS = {"role", "content", "tool_calls", "tool_call_id", "name"}


def for_api(messages: list) -> list:
    """把内部消息清洗成 API 能接受的样子。

    1. 我们会往消息里塞自己的字段（比如 extra），API 不认识
    2. 模型可能返回 reasoning_content 等额外字段，原样发回去可能报错
    3. content 为 None 时有些 API 会拒绝，统一换成空字符串
    """
    out = []
    for m in messages:
        d = {k: v for k, v in m.items() if k in API_FIELDS}
        if d.get("content") is None:
            d["content"] = ""
        out.append(d)
    return out


# ==================================================================
# 父类：管状态。query() 返回一条【消息字典】
# ==================================================================
class Model:
    def __init__(self, cost_limit: float = 0.5, tools: list = None):
        self.n_calls = 0
        self.total_cost = 0.0
        self.cost_limit = cost_limit
        self.tools = tools if tools is not None else ALL_TOOLS

    def query(self, messages: list) -> dict:
        if 0 < self.cost_limit <= self.total_cost:
            raise BudgetExceeded(
                f"预算用尽：已花 ${self.total_cost:.4f}，上限 ${self.cost_limit:.4f}"
            )
        self.n_calls += 1
        message, cost = self._generate(messages)
        self.total_cost += cost
        return message

    def _generate(self, messages: list):
        raise NotImplementedError("子类必须实现 _generate()，返回 (消息dict, 花费)")

    def stats(self) -> str:
        return f"调用 {self.n_calls} 次，累计 ${self.total_cost:.4f}"


# ==================================================================
# 子类 1：真的调 DeepSeek
# ==================================================================
class DeepSeekModel(Model):
    # ⚠️ 费率会变，以 https://api-docs.deepseek.com/quick_start/pricing 为准
    PRICE_INPUT = 0.27 / 1_000_000
    PRICE_OUTPUT = 1.10 / 1_000_000

    def __init__(self, model_name: str = "deepseek-chat", cost_limit: float = 0.5, **kw):
        super().__init__(cost_limit=cost_limit, **kw)
        self.model_name = model_name
        self.env = load_env()

    def _generate(self, messages: list):
        url = self.env["DEEPSEEK_BASE_URL"].rstrip("/") + "/chat/completions"
        payload = json.dumps({
            "model": self.model_name,
            "messages": for_api(messages),
            "tools": self.tools,
        }).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + self.env["DEEPSEEK_API_KEY"],
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=180) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        choice = data["choices"][0]
        message = choice["message"]
        message.setdefault("content", "")
        message["extra"] = {"finish_reason": choice.get("finish_reason")}

        usage = data.get("usage", {})
        cost = (usage.get("prompt_tokens", 0) * self.PRICE_INPUT
                + usage.get("completion_tokens", 0) * self.PRICE_OUTPUT)
        return message, cost


# ==================================================================
# 子类 2：假模型 —— 伪造和真 API 一模一样的 tool_calls
# ==================================================================
def make_tool_call(tool_name: str, args: dict, seq: int) -> dict:
    return {
        "id": f"call_mock_{seq}",
        "type": "function",
        "function": {"name": tool_name, "arguments": json.dumps(args, ensure_ascii=False)},
    }


# 台词格式：(thought文字, (tool_name, args字典) 或 None)
DEFAULT_SCRIPT = [
    ("我先看看有什么文件。", ("bash", {"command": "ls"})),
    ("看一下 demo.py 的内容。", ("bash", {"command": "nl -ba demo.py"})),
    ("给 div 加上除零检查 —— 用 edit_file，不重写整个文件。",
     ("edit_file", {"path": "demo.py",
                    "old": "    return a / b",
                    "new": '    if b == 0:\n        raise ValueError("除数不能为0")\n    return a / b'})),
    ("再跑一遍验证。", ("bash", {"command": "python3 demo.py"})),
    ("（故意演示：这次不调用任何工具）", None),
    ("好了，任务完成。", ("bash", {"command": "echo TASK_DONE"})),
    # ↓ 上面那句会触发"完成前自检"，所以还要再准备一轮
    ("自检：\n"
     "1. 任务要求：给 demo.py 的 div 加除零检查\n"
     "2. 做到了 —— 第 3 步用 edit_file 加了 if b == 0 raise ValueError，"
     "第 4 步运行验证通过\n"
     "3. 没有做任务之外的改动\n"
     "4. 结论：可以结束",
     ("bash", {"command": "echo TASK_DONE"})),
]


class MockModel(Model):
    def __init__(self, scripted: list = None, cost_limit: float = 0.0, **kw):
        super().__init__(cost_limit=cost_limit, **kw)
        self.scripted = scripted if scripted is not None else DEFAULT_SCRIPT
        self.i = 0

    def _generate(self, messages: list):
        if self.i >= len(self.scripted):
            raise IndexError(f"台词用完了（共 {len(self.scripted)} 句）")
        thought, call = self.scripted[self.i]
        self.i += 1
        message = {"role": "assistant", "content": thought, "extra": {}}
        if call is not None:
            tool_name, args = call
            message["tool_calls"] = [make_tool_call(tool_name, args, self.i)]
        return message, 0.0


# ==================================================================
if __name__ == "__main__":
    print("=== 默认带哪些工具 ===")
    for cls in (DeepSeekModel, MockModel):
        m = cls()
        print(f"   {cls.__name__:15s} -> {[t['function']['name'] for t in m.tools]}")

    print("\n=== MockModel 能造两种工具call ===")
    m = MockModel()
    for _ in range(4):
        msg = m.query([])
        tc = (msg.get("tool_calls") or [None])[0]
        if tc:
            print(f"\n   content = {msg['content']}")
            print(f"   tool_name  = {tc['function']['name']}")
            print(f"   args    = {tc['function']['arguments']}")
