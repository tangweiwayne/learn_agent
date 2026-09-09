"""端到端测 _generate_stream()：伪造一个 SSE 响应，不联网、不花钱。

做法：把 urllib.request.urlopen 换成我们自己的假函数，
让它返回一个"能被 for 循环逐行读"的假响应对象。

跑法：  python3 test_stream_http.py
"""
import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import v3_model
from v3_model import DeepSeekModel

# ---------- 伪造服务器一行一行吐出来的东西 ----------
SSE_LINES = [
    'data: {"choices":[{"index":0,"delta":{"role":"assistant","content":""}}]}',
    '',                                                   # SSE 规定每条之间有空行
    'data: {"choices":[{"index":0,"delta":{"content":"我先"}}]}',
    '',
    'data: {"choices":[{"index":0,"delta":{"content":"看一下"}}]}',
    '',
    'data: {"choices":[{"index":0,"delta":{"content":" discount.py"}}]}',
    '',
    'data: {"choices":[{"index":0,"delta":{"content":"。"}}]}',
    '',
    'data: {"choices":[{"index":0,"delta":{"tool_calls":[{"index":0,"id":"call_0_abc",'
    '"type":"function","function":{"name":"bash","arguments":""}}]}}]}',
    '',
    'data: {"choices":[{"index":0,"delta":{"tool_calls":[{"index":0,'
    '"function":{"arguments":"{\\""}}]}}]}',
    '',
    'data: {"choices":[{"index":0,"delta":{"tool_calls":[{"index":0,'
    '"function":{"arguments":"command\\":\\"nl -ba disc"}}]}}]}',
    '',
    'data: {"choices":[{"index":0,"delta":{"tool_calls":[{"index":0,'
    '"function":{"arguments":"ount.py\\"}"}}]}}]}',
    '',
    'data: {"choices":[{"index":0,"delta":{},"finish_reason":"tool_calls"}]}',
    '',
    # ★ usage 只在这一块里，而且这块的 choices 是空的
    'data: {"choices":[],"usage":{"prompt_tokens":1523,"completion_tokens":47}}',
    '',
    'data: [DONE]',
]


class FakeResponse:
    """假装是 urlopen 返回的东西：能 with，能 for。"""

    def __init__(self, lines):
        self.lines = lines

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def __iter__(self):
        for line in self.lines:
            yield (line + "\n").encode("utf-8")     # 真实的 resp 吐的是 bytes


captured = {}


def fake_urlopen(req, timeout=None):
    captured["body"] = json.loads(req.data.decode("utf-8"))
    return FakeResponse(SSE_LINES)


# ---------- 开测 ----------
urllib.request.urlopen = fake_urlopen          # 偷梁换柱
v3_model.urllib.request.urlopen = fake_urlopen

printed = []
model = DeepSeekModel(cost_limit=1.0, stream=True,
                      on_text=lambda p: printed.append(p))

message = model.query([{"role": "user", "content": "修好 buggy.py"}],
                      tools=[{"type": "function",
                              "function": {"name": "bash", "parameters": {}}}])

print("① 发出去的 body 里有没有 stream 开关：")
print("   stream         =", captured["body"].get("stream"))
print("   stream_options =", captured["body"].get("stream_options"))

print("\n② 边收边打印出来的碎片（on_text 收到的）：")
print("  ", printed)
print("   拼起来 =", repr("".join(printed)))

print("\n③ 攒完的 message：")
print("  ", json.dumps(message, ensure_ascii=False, indent=2))

print("\n④ arguments 能不能解析：")
args = json.loads(message["tool_calls"][0]["function"]["arguments"])
print("  ", args)

print("\n⑤ 钱算出来了吗（usage 藏在倒数第二块）：")
print(f"   total_cost = ${model.total_cost:.6f}")
print(f"   手算       = ${1523 * 0.27/1e6 + 47 * 1.10/1e6:.6f}")

ok = (message["content"] == "我先看一下 discount.py。"
      and args == {"command": "nl -ba discount.py"}
      and message["extra"]["finish_reason"] == "tool_calls"
      and abs(model.total_cost - (1523 * 0.27/1e6 + 47 * 1.10/1e6)) < 1e-12
      and captured["body"]["stream"] is True)
print("\n" + ("✅ 全部通过" if ok else "❌ 有问题"))
