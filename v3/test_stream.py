"""测 StreamAccumulator：喂碎片，看能不能攒回和非流式一模一样的消息。"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v3_model import StreamAccumulator

# ---------- 用例 1：一段正文 + 一个工具调用，arguments 碎在 JSON 语法中间 ----------
DELTAS_1 = [
    {"role": "assistant", "content": ""},
    {"content": "我先"},
    {"content": "看一下"},
    {"content": " discount.py"},
    {"content": "。"},
    {"tool_calls": [{"index": 0, "id": "call_0_abc", "type": "function",
                     "function": {"name": "bash", "arguments": ""}}]},
    {"tool_calls": [{"index": 0, "function": {"arguments": '{"'}}]},
    {"tool_calls": [{"index": 0, "function": {"arguments": "command"}}]},
    {"tool_calls": [{"index": 0, "function": {"arguments": '":"nl'}}]},
    {"tool_calls": [{"index": 0, "function": {"arguments": " -ba disc"}}]},
    {"tool_calls": [{"index": 0, "function": {"arguments": 'ount.py"}'}}]},
    {},
]

EXPECT_1 = {
    "role": "assistant",
    "content": "我先看一下 discount.py。",
    "tool_calls": [{
        "id": "call_0_abc", "type": "function",
        "function": {"name": "bash",
                     "arguments": '{"command":"nl -ba discount.py"}'},
    }],
}

# ---------- 用例 2：一次调两个工具，碎片【交错】到达 ----------
DELTAS_2 = [
    {"content": "我同时看两个文件。"},
    {"tool_calls": [{"index": 0, "id": "call_A", "type": "function",
                     "function": {"name": "bash", "arguments": ""}}]},
    {"tool_calls": [{"index": 1, "id": "call_B", "type": "function",
                     "function": {"name": "bash", "arguments": ""}}]},
    {"tool_calls": [{"index": 0, "function": {"arguments": '{"comm'}}]},
    {"tool_calls": [{"index": 1, "function": {"arguments": '{"comm'}}]},   # 交错
    {"tool_calls": [{"index": 0, "function": {"arguments": 'and":"cat a.py"}'}}]},
    {"tool_calls": [{"index": 1, "function": {"arguments": 'and":"cat b.py"}'}}]},
]

EXPECT_2 = {
    "role": "assistant",
    "content": "我同时看两个文件。",
    "tool_calls": [
        {"id": "call_A", "type": "function",
         "function": {"name": "bash", "arguments": '{"command":"cat a.py"}'}},
        {"id": "call_B", "type": "function",
         "function": {"name": "bash", "arguments": '{"command":"cat b.py"}'}},
    ],
}

# ---------- 用例 3：只说话，不调工具 ----------
DELTAS_3 = [{"content": "任务"}, {"content": "已完成。"}]
EXPECT_3 = {"role": "assistant", "content": "任务已完成。"}


def run(name, deltas, expect):
    acc = StreamAccumulator()
    printed = "".join(acc.feed(d) for d in deltas)   # feed 的返回值 = 该实时打印的
    got = acc.message()
    ok = got == expect
    print(f"{'✅' if ok else '❌'} {name}")
    if not ok:
        print("  期望:", json.dumps(expect, ensure_ascii=False))
        print("  实得:", json.dumps(got, ensure_ascii=False))
        return False
    # 攒完的 arguments 必须是合法 JSON
    for tc in got.get("tool_calls", []):
        args = json.loads(tc["function"]["arguments"])
        print(f"     └ {tc['function']['name']}({args}) ← json.loads 通过")
    if printed:
        print(f"     └ 实时打印出来的正文: {printed!r}")
    return True


all_ok = all([
    run("用例1 单工具，arguments 碎在 JSON 语法中间", DELTAS_1, EXPECT_1),
    run("用例2 双工具，碎片交错到达", DELTAS_2, EXPECT_2),
    run("用例3 只说话不调工具", DELTAS_3, EXPECT_3),
])

# ---------- 用例 4：中途每一块单独 json.loads 都会炸，证明必须先拼 ----------
print("\n为什么必须先拼完再解析：")
part = ""
for d in DELTAS_1:
    for tc in d.get("tool_calls") or []:
        part += (tc.get("function") or {}).get("arguments", "")
        if not part:
            continue
        try:
            json.loads(part)
            print(f"  {part!r:42} → 解析成功 ✅")
        except json.JSONDecodeError:
            print(f"  {part!r:42} → JSONDecodeError ❌")

print("\n" + ("全部通过" if all_ok else "有失败"))
