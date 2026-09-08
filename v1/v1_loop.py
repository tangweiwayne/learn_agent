"""
=============================================================
 第一课：从零手写一个 AI Agent —— 核心就是一个 while 循环
=============================================================

零依赖版本：只用 Python 标准库，不需要 pip install 任何东西。

运行：
    python3 v1_loop.py --mock                 # 离线演示，看清流程
    python3 v1_loop.py "建一个 hello.py 并运行"   # 真实调用 DeepSeek
"""

import json
import os
import re
import subprocess
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))


# ==================================================================
# 函数 1 / load_env —— 读 .env 文件，拿到 API key
# ==================================================================
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


ENV = load_env()


# ==================================================================
# 函数 2 / SYSTEM_PROMPT —— 不是函数，但它是整个 agent 最重要的部分
# ==================================================================
# 关键洞察：mini-swe-agent 不给模型任何自定义工具（没有 read_file / edit_file /
# search）。只有 bash。因为 bash 本身就是最强的工具集：cat / sed / grep /
# python / git……模型自己会用。
#
# 换句话说：agent 的"能力"不在代码里，在这段提示词里。
SYSTEM_PROMPT = """你是一个能操作电脑的助手。你唯一的工具是 bash。

你的每次回复必须包含：先写一段思考，然后**恰好一个** bash 代码块。

格式示例：
我需要先看看目录里有什么。

```bash
ls -la
```

规则：
1. 每次回复只能有一个代码块，一条命令（可以用 && 连接）。
2. 每条命令都在**新的子进程**里执行，所以 cd 和环境变量不会保留。
   需要的话就写成 `cd /path && your_command`。
3. 任务完成后，单独回复这条命令来结束（不要和别的命令连在一起）：
   ```bash
   echo TASK_DONE
   ```
"""


# ==================================================================
# 函数 3 / query_llm —— 把对话发给 LLM，拿回一段文字
# ==================================================================
def query_llm(messages: list) -> str:
    """一次 HTTP POST。用标准库 urllib，让你看清楚请求长什么样。

    注意：这里没有任何"记忆"魔法 —— 所谓记忆，就是把整个 messages
    列表原样再发一遍。LLM 本身是无状态的。
    """
    url = ENV["DEEPSEEK_BASE_URL"].rstrip("/") + "/chat/completions"
    payload = json.dumps(
        {"model": "deepseek-chat", "messages": messages}
    ).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + ENV["DEEPSEEK_API_KEY"],
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"]


# ==================================================================
# 函数 4 / parse_action —— 从自由文本里抠出那条 bash 命令
# ==================================================================
def parse_action(text: str) -> str:
    """找 ```bash ... ``` 代码块。必须不多不少恰好一个。

    为什么这么严格？因为如果模型一次给三条命令，执行完第一条环境就变了，
    后两条可能就不该执行了。agent 必须每走一步、看一眼。
    """
    blocks = re.findall(r"```bash\n(.*?)\n```", text, re.DOTALL)
    if len(blocks) != 1:
        raise ValueError(f"需要恰好 1 个 bash 代码块，实际找到 {len(blocks)} 个")
    return blocks[0].strip()


# ==================================================================
# 函数 5 / execute —— 真的把命令跑起来
# ==================================================================
def execute(command: str) -> str:
    """用 subprocess 执行，每次都是全新子进程。

    这是 mini-swe-agent 最重要的设计决定：不维护长期存活的 shell 会话。
    代价是 cd 不保留；换来的是无状态、可沙箱化、永不卡死。
    """
    try:
        r = subprocess.run(
            command, shell=True, text=True, capture_output=True,
            timeout=30, cwd=os.getcwd(),
        )
        returncode, output = r.returncode, r.stdout + r.stderr
    except subprocess.TimeoutExpired:
        returncode, output = -1, "命令超时（30秒）"
    return f"<returncode>{returncode}</returncode>\n<output>\n{output}</output>"


# ==================================================================
# 函数 6 / run —— 把上面几块串成一个循环。这就是 agent 的全部。
# ==================================================================
def run(task: str, model=query_llm, step_limit: int = 20) -> list:
    # messages 就是 agent 的"全部状态"。没有别的东西。
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"请完成这个任务：{task}"},
    ]

    for step in range(1, step_limit + 1):
        # --- (a) 问模型 ---
        reply = model(messages)
        messages.append({"role": "assistant", "content": reply})
        print(f"\n\033[31m===== 第 {step} 步 · 模型说 =====\033[0m\n{reply}")

        # --- (b) 解析出命令 ---
        try:
            command = parse_action(reply)
        except ValueError as e:
            # 格式错了不要崩：把错误当成一条"用户消息"喂回去，让模型自己改
            messages.append({"role": "user", "content": f"格式错误：{e}，请重发。"})
            print(f"\033[33m[格式错误] {e}\033[0m")
            continue

        # --- (c) 执行 ---
        observation = execute(command)
        print(f"\033[32m----- 执行结果 -----\033[0m\n{observation}")

        # --- (d) 判断是否结束：退出也只是一条普通 bash 命令 ---
        if command.strip() == "echo TASK_DONE":
            print("\n\033[36m✅ 任务结束\033[0m")
            return messages

        # --- (e) 把结果贴回对话，进入下一轮 ---
        messages.append({"role": "user", "content": observation})

    print("\n\033[33m⚠️ 达到步数上限，强制停止\033[0m")
    return messages


# ==================================================================
# 函数 7 / make_mock_model —— 离线演示用的"假模型"
# ==================================================================
def make_mock_model():
    """返回一个和 query_llm 签名一样的函数，但不联网，只念预设台词。

    这叫依赖注入：run() 不关心 model 是真是假，只要能调用就行。
    真实仓库里也是这么做的 —— DefaultAgent(model, env) 两个参数都可替换。
    """
    scripted = [
        "我先看看当前目录里有什么文件。\n\n```bash\nls\n```",
        "有几个文件。现在数一下 .py 文件的数量。\n\n```bash\nls *.py | wc -l\n```",
        "（故意演示一次格式错误：我忘了写代码块）",
        "抱歉，重新发。数完了，任务完成。\n\n```bash\necho TASK_DONE\n```",
    ]
    it = iter(scripted)
    return lambda messages: next(it)


if __name__ == "__main__":
    if "--mock" in sys.argv:
        run("统计当前目录有多少个 .py 文件", model=make_mock_model())
    else:
        task = sys.argv[1] if len(sys.argv) > 1 else input("任务：")
        run(task)
