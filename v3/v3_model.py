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
# 发给 API 之前，只keep API 认识的字段
# ==================================================================
API_FIELDS = {"role", "content", "tool_calls", "tool_call_id", "name"}


# ==================================================================
# 流式输出：把一堆 delta 碎片攒回一条完整消息
# ==================================================================
class StreamAccumulator:
    """收 SSE 的 delta 碎片，攒成一条和【非流式】完全一样的 message。

    用法：
        acc = StreamAccumulator()
        for delta in 每一块:
            acc.feed(delta)
        message = acc.message()
    """

    def __init__(self):
        self.content_parts = []   # content 的碎片，最后 "".join 起来
        self.calls = {}           # index -> 这个工具调用攒到哪了

    def feed(self, delta: dict) -> str:
        """吃一块 delta，返回【这一块新增的正文】（好让调用方立刻打印出来）。"""
        piece = delta.get("content") or ""
        if piece:
            self.content_parts.append(piece)

        for tc in delta.get("tool_calls") or []:
            i = tc.get("index", 0)
            slot = self.calls.setdefault(
                i, {"id": "", "type": "function",
                    "function": {"name": "", "arguments": ""}})
            if tc.get("id"):
                slot["id"] = tc["id"]
            if tc.get("type"):
                slot["type"] = tc["type"]
            fn = tc.get("function") or {}
            if fn.get("name"):
                slot["function"]["name"] = fn["name"]
            if fn.get("arguments"):
                slot["function"]["arguments"] += fn["arguments"]

        return piece

    def message(self) -> dict:
        """攒完了，输出一条标准 assistant 消息。"""
        out = {"role": "assistant", "content": "".join(self.content_parts)}
        if self.calls:
            # 按 index 排好序再输出，别指望字典顺序
            out["tool_calls"] = [self.calls[i] for i in sorted(self.calls)]
        return out


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
    def __init__(self, cost_limit: float = 0.5, tools: list = None,
                 stream: bool = False, on_text=None):
        self.n_calls = 0
        self.total_cost = 0.0
        self.cost_limit = cost_limit
        self.tools = tools if tools is not None else ALL_TOOLS
        self.stream = stream        # 要不要边生成边收
        self.on_text = on_text      # 每收到一小段正文就调一次：on_text("我先")

    def query(self, messages: list, tools: list = None) -> dict:
        """tools 传了就用传的，没传就用 self.tools。

        为什么要能传：主 agent 和子 agent 共用同一个 Model 实例
        （这样花费自动累加到一起），但它们能用的工具不一样。
        """
        if 0 < self.cost_limit <= self.total_cost:
            raise BudgetExceeded(
                f"预算用尽：已花 ${self.total_cost:.4f}，上限 ${self.cost_limit:.4f}"
            )
        self.n_calls += 1
        message, cost = self._generate(messages, tools if tools is not None else self.tools)
        self.total_cost += cost
        return message

    def _generate(self, messages: list, tools: list):
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

    def _build_request(self, messages: list, tools: list, stream: bool):
        """两条路（流式/非流式）唯一的差别就是 body 里多两个字段。"""
        body = {
            "model": self.model_name,
            "messages": for_api(messages),
            "tools": tools,
        }
        if stream:
            body["stream"] = True
            # ★ 不加这个，流式响应里【不会】带 usage，就算不出钱
            body["stream_options"] = {"include_usage": True}
        return urllib.request.Request(
            self.env["DEEPSEEK_BASE_URL"].rstrip("/") + "/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + self.env["DEEPSEEK_API_KEY"],
            },
            method="POST",
        )

    def _cost(self, usage: dict) -> float:
        return (usage.get("prompt_tokens", 0) * self.PRICE_INPUT
                + usage.get("completion_tokens", 0) * self.PRICE_OUTPUT)

    def _generate(self, messages: list, tools: list):
        if self.stream:
            return self._generate_stream(messages, tools)
        return self._generate_blocking(messages, tools)

    # ---------- 路 A：一次性拿完整 JSON（原来的做法）----------
    def _generate_blocking(self, messages: list, tools: list):
        req = self._build_request(messages, tools, stream=False)
        with urllib.request.urlopen(req, timeout=180) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        choice = data["choices"][0]
        message = choice["message"]
        message.setdefault("content", "")
        message["extra"] = {"finish_reason": choice.get("finish_reason")}
        return message, self._cost(data.get("usage", {}))

    # ---------- 路 B：逐行读 SSE ----------
    def _generate_stream(self, messages: list, tools: list):
        req = self._build_request(messages, tools, stream=True)
        acc = StreamAccumulator()
        usage, finish_reason = {}, None

        with urllib.request.urlopen(req, timeout=180) as resp:
            for raw_line in resp:                     # ← 有一行读一行，不等全部
                line = raw_line.decode("utf-8").strip()
                if not line or not line.startswith("data:"):
                    continue                          # 空行和心跳，跳过
                body = line[len("data:"):].strip()
                if body == "[DONE]":
                    break                             # 结束标记，不是 JSON
                chunk = json.loads(body)

                if chunk.get("usage"):
                    usage = chunk["usage"]            # 只在最后一两块里出现

                for choice in chunk.get("choices") or []:
                    piece = acc.feed(choice.get("delta") or {})
                    if piece and self.on_text:
                        self.on_text(piece)           # ← 立刻交给外面打印
                    if choice.get("finish_reason"):
                        finish_reason = choice["finish_reason"]

        message = acc.message()
        message["extra"] = {"finish_reason": finish_reason}
        return message, self._cost(usage)


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
    ("先把任务拆成计划。",
     ("update_plan", {"steps": [
         {"text": "看清 demo.py 里 div 的原文", "status": "doing"},
         {"text": "给 div 加除零检查", "status": "todo"},
         {"text": "运行验证", "status": "todo"}]})),
    ("我先看看有什么文件。", ("bash", {"command": "ls"})),
    ("看一下 demo.py 的内容。", ("bash", {"command": "nl -ba demo.py"})),
    ("给 div 加上除零检查 —— 用 edit_file，不重写整个文件。",
     ("edit_file", {"path": "demo.py",
                    "old": "    return a / b",
                    "new": '    if b == 0:\n        raise ValueError("除数不能为0")\n    return a / b'})),
    ("第 1、2 步做完了，打勾。",
     ("update_plan", {"steps": [
         {"text": "看清 demo.py 里 div 的原文", "status": "done"},
         {"text": "给 div 加除零检查", "status": "done"},
         {"text": "运行验证", "status": "doing"}]})),
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

    def _generate(self, messages: list, tools: list = None):
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
