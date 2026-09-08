"""
v3 · 改动 1：用【工具调用】替代正则解析

和 v2 的差别：
  · 请求里多带一个 tools=[BASH_TOOL]，告诉 API "有个叫 bash 的工具"
  · 模型返回的不再是一坨文字，而是结构化的 tool_calls
  · query() 返回【整条 assistant 消息】，不再是字符串
  · 不再需要 parse_action() 和正则
"""

import json
import os
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))


# ==================================================================
# 工具定义：告诉 API "我有一个叫 bash 的工具，长这样"
# 这是 OpenAI 定的标准格式，DeepSeek / Claude / Gemini 都兼容
# ==================================================================
BASH_TOOL = {
    "type": "function",
    "function": {
        "name": "bash",
        "description": (
            "在用户的电脑上执行一条 bash 命令，返回它的标准输出和错误输出。"
            "每条命令都在新的子进程里执行，cd 和环境变量不会保留到下一条。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "要执行的完整 bash 命令，可以是多行",
                }
            },
            "required": ["command"],
        },
    },
}


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

    为什么需要：
      1. 我们会往消息里塞自己的字段（比如 extra），API 不认识
      2. DeepSeek 会返回 reasoning_content 等额外字段，原样发回去可能报错
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
# 父类：管状态（和 v2 一样），但 query 返回的是【一条消息】
# ==================================================================
class Model:
    def __init__(self, cost_limit: float = 0.5, tools: list = None):
        self.n_calls = 0
        self.total_cost = 0.0
        self.cost_limit = cost_limit
        self.tools = tools if tools is not None else [BASH_TOOL]

    def query(self, messages: list) -> dict:
        """返回一条 assistant 消息（dict），里面可能带 tool_calls。"""
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
        payload = json.dumps(
            {
                "model": self.model_name,
                "messages": for_api(messages),
                "tools": self.tools,          # ← 这是 v3 的核心新增
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
        with urllib.request.urlopen(req, timeout=180) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        choice = data["choices"][0]
        message = choice["message"]           # 已经是标准格式，含 tool_calls
        message.setdefault("content", "")
        message["extra"] = {"finish_reason": choice.get("finish_reason")}

        usage = data.get("usage", {})
        cost = (usage.get("prompt_tokens", 0) * self.PRICE_INPUT
                + usage.get("completion_tokens", 0) * self.PRICE_OUTPUT)
        return message, cost


# ==================================================================
# 子类 2：假模型 —— 现在要伪造 tool_calls 格式
# ==================================================================
def 造一条工具调用(command: str, 序号: int) -> dict:
    """手工拼一个和真 API 返回一模一样的 tool_call。"""
    return {
        "id": f"call_mock_{序号}",
        "type": "function",
        "function": {"name": "bash", "arguments": json.dumps({"command": command})},
    }


# 台词格式：(思考文字, 命令 或 None)   None 表示"这次故意不调用工具"
DEFAULT_SCRIPT = [
    ("我先看看当前目录里有什么文件。", "ls"),
    ("有几个文件，数一下 .py 的数量。", "ls *.py | wc -l"),
    ("（故意演示：这次不调用任何工具）", None),
    ("抱歉，数完了，任务完成。", "echo TASK_DONE"),
]


class MockModel(Model):
    def __init__(self, scripted: list = None, cost_limit: float = 0.0, **kw):
        super().__init__(cost_limit=cost_limit, **kw)
        self.scripted = scripted if scripted is not None else DEFAULT_SCRIPT
        self.i = 0

    def _generate(self, messages: list):
        if self.i >= len(self.scripted):
            raise IndexError(f"台词用完了（共 {len(self.scripted)} 句）")
        思考, 命令 = self.scripted[self.i]
        self.i += 1
        message = {"role": "assistant", "content": 思考}
        if 命令 is not None:
            message["tool_calls"] = [造一条工具调用(命令, self.i)]
        return message, 0.0


# ------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 66)
    print("=== 1. MockModel 返回的消息长什么样 ===")
    m = MockModel()
    msg = m.query([])
    print(json.dumps(msg, ensure_ascii=False, indent=2))

    print("\n=== 2. 怎么从里面取出命令 ===")
    tc = msg["tool_calls"][0]
    args = json.loads(tc["function"]["arguments"])
    print(f"   tool_call id  = {tc['id']}")
    print(f"   工具名        = {tc['function']['name']}")
    print(f"   arguments     = {tc['function']['arguments']!r}   ← 是个 JSON 字符串")
    print(f"   json.loads 后 = {args}")
    print(f"   命令          = {args['command']!r}")

    print("\n=== 3. 第 3 句台词故意不带工具调用 ===")
    m.query([])                                    # 第 2 句
    msg3 = m.query([])                             # 第 3 句
    print(f"   content    = {msg3['content']!r}")
    print(f"   有 tool_calls 吗 = {'tool_calls' in msg3}   ← 没有，agent 要处理这种情况")

    print("\n=== 4. for_api() 清洗字段 ===")
    脏消息 = [
        {"role": "assistant", "content": None, "tool_calls": [tc],
         "reasoning_content": "这是 DeepSeek 多给的字段", "extra": {"我的": "私货"}},
        {"role": "tool", "tool_call_id": "call_x", "content": "输出"},
    ]
    print("   清洗前的键：", [sorted(d) for d in 脏消息])
    print("   清洗后的键：", [sorted(d) for d in for_api(脏消息)])
    print("   content=None 被换成了:", repr(for_api(脏消息)[0]["content"]))
