"""mini-swe-agent 第三讲：action 如何变成 tool 观察消息。

不联网，只演示数据流。
运行：python3 mswea/mswea03_action到tool消息.py
"""

import json
import subprocess


def environment_execute(action: dict) -> dict:
    """缩小版 LocalEnvironment.execute：执行 action，返回原始事实。"""
    result = subprocess.run(
        action.get("command", ""),
        shell=True,
        text=True,
        capture_output=True,
        timeout=5,
    )
    return {
        "output": result.stdout + result.stderr,
        "returncode": result.returncode,
        "exception_info": "",
    }


def format_observation(action: dict, output: dict) -> dict:
    """缩小版 Model.format_observation_messages：把原始结果包成消息。"""
    return {
        "role": "tool",
        "tool_call_id": action["tool_call_id"],
        "content": (
            f"<returncode>{output['returncode']}</returncode>\n"
            f"<output>\n{output['output']}</output>"
        ),
        "extra": {
            "raw_output": output["output"],
            "returncode": output["returncode"],
            "exception_info": output["exception_info"],
        },
    }


# 上一讲 Model 已经翻译好的 action。
action = {
    "command": "printf 'main.py\\ntest_main.py\\n'",
    "tool_call_id": "call_123",
}

print("① Agent 从 message['extra']['actions'] 取出 action")
print(json.dumps(action, ensure_ascii=False, indent=2))

output = environment_execute(action)
print("\n② Environment 执行后返回原始字典")
print(repr(output))

tool_message = format_observation(action, output)
print("\n③ Model 把原始字典格式化成 tool 消息")
print(json.dumps(tool_message, ensure_ascii=False, indent=2))

messages = [
    {"role": "system", "content": "你是 coding agent。"},
    {"role": "user", "content": "查看目录。"},
    {
        "role": "assistant",
        "content": "我先查看文件。",
        "tool_calls": [{"id": "call_123"}],
        "extra": {"actions": [action]},
    },
    tool_message,
]

print("\n④ 加入 messages，下一轮 Model 能看到这个结果")
print([message["role"] for message in messages])
print("请求 id:", messages[2]["tool_calls"][0]["id"])
print("结果 id:", messages[3]["tool_call_id"])

assert messages[2]["tool_calls"][0]["id"] == messages[3]["tool_call_id"]
assert "main.py" in messages[3]["content"]
print("\n✅ action 已执行，并与对应的 tool 结果配对")
