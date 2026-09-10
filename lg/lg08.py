"""真·LangGraph agent：换上真 DeepSeek。

    python3 lg08.py --mock "任务"    假模型，不花钱（验证接线）
    python3 lg08.py "任务"           真 DeepSeek
"""
import os
import subprocess
import sys
import tempfile
from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

DONE_MARKER = "TASK_DONE"
CWD = os.getcwd()


# ============ ① 工具：一个函数 + 一个装饰器 ============
@tool
def bash(command: str) -> str:
    """在电脑上执行一条 bash 命令，返回标准输出和错误输出。

    用它来查看文件（cat / nl -ba / grep）、搜索、运行程序和测试。
    每条命令都在新的子进程里执行，cd 不会保留到下一条。
    """
    r = subprocess.run(command, shell=True, cwd=CWD,
                       capture_output=True, text=True, timeout=30)
    out = (r.stdout or "") + (r.stderr or "")
    if len(out) > 4000:
        out = out[:2000] + "\n…（中间省略）…\n" + out[-2000:]
    return f"<returncode>{r.returncode}</returncode>\n<output>\n{out}</output>"


TOOLS = [bash]
TOOLS_BY_NAME = {t.name: t for t in TOOLS}


# ============ ② 模型 ============
def load_env():
    """读 learn_agent/.env，同 v3 的做法：从本文件往上找。"""
    here = os.path.dirname(os.path.abspath(__file__))
    for _ in range(4):
        p = os.path.join(here, ".env")
        if os.path.exists(p):
            env = {}
            for line in open(p, encoding="utf-8"):
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip().strip("'\"")
            return env
        here = os.path.dirname(here)
    raise FileNotFoundError("找不到 .env")


def build_llm(mock: bool):
    if mock:
        from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
        script = [
            AIMessage(content="我先看看目录里有什么。",
                      tool_calls=[{"name": "bash", "args": {"command": "ls -la"},
                                   "id": "c1"}]),
            AIMessage(content="干完了。",
                      tool_calls=[{"name": "bash",
                                   "args": {"command": f"echo {DONE_MARKER}"},
                                   "id": "c2"}]),
        ]
        return GenericFakeChatModel(messages=iter(script))

    from langchain_openai import ChatOpenAI
    env = load_env()
    return ChatOpenAI(
        model="deepseek-chat",
        api_key=env["DEEPSEEK_API_KEY"],
        base_url=env["DEEPSEEK_BASE_URL"],
        temperature=0,
    ).bind_tools(TOOLS)          # ★ 把工具挂上去


# ============ ③ 图 ============
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]


def make_graph(llm):
    def call_model(state):
        message = llm.invoke(state["messages"])
        print(f"\n\033[31m===== 模型说 =====\n{message.content or '(没说话)'}\033[0m")
        for tc in message.tool_calls:
            print(f"\033[35m  🔧 {tc['name']}: {tc['args']}\033[0m")
        return {"messages": [message]}

    def run_tools(state):
        last = state["messages"][-1]
        out = []
        for tc in last.tool_calls:
            fn = TOOLS_BY_NAME.get(tc["name"])
            observation = (fn.invoke(tc["args"]) if fn
                           else f"<error>没有叫 {tc['name']} 的工具</error>")
            print(f"\033[32m----- 执行结果 -----\n{observation}\033[0m")
            out.append(ToolMessage(content=observation, tool_call_id=tc["id"]))
        return {"messages": out}

    def should_continue(state):
        last = state["messages"][-1]
        if isinstance(last, ToolMessage):
            if any(l.strip() == DONE_MARKER for l in last.content.splitlines()):
                return "done"
            return "call_model"
        return "done" if not last.tool_calls else "run_tools"

    builder = StateGraph(AgentState)
    builder.add_node("call_model", call_model)
    builder.add_node("run_tools", run_tools)
    builder.add_edge(START, "call_model")
    builder.add_conditional_edges("call_model", should_continue,
                                  {"run_tools": "run_tools", "done": END})
    builder.add_conditional_edges("run_tools", should_continue,
                                  {"call_model": "call_model", "done": END})
    return builder.compile()


SYSTEM = f"""你是一个能操作电脑的助手。你有一个工具：bash。
始终用中文说明你的思考和结论（命令本身不受影响）。
每一步：先简短说明你要做什么和为什么，然后调用 bash 执行一条命令。
看到结果后再决定下一步 —— 不要凭猜测连续动作。
注意：每条命令都在新的子进程里执行，cd 不会保留到下一条。
任务完成后，调用 bash 执行 `echo {DONE_MARKER}` 来结束。"""


if __name__ == "__main__":
    args = sys.argv[1:]
    mock = "--mock" in args
    task = next((a for a in args if not a.startswith("--")), None) or "列出当前目录的文件"

    if mock:
        CWD = tempfile.mkdtemp()
    print(f"\n[LangGraph 版] 模式: {'mock' if mock else 'DeepSeek'}")
    print(f"目录: {CWD}\n")

    app = make_graph(build_llm(mock))
    final = app.invoke(
        {"messages": [SystemMessage(content=SYSTEM),
                      HumanMessage(content=f"请完成这个任务：{task}")]},
        config={"recursion_limit": 40},
    )

    # ---- 统计：步数 + 花费（每条 AIMessage 自带 usage_metadata）----
    PRICE_IN, PRICE_OUT = 0.27 / 1e6, 1.10 / 1e6
    steps = cost = tok_in = tok_out = 0
    for m in final["messages"]:
        if not isinstance(m, AIMessage):
            continue
        steps += 1
        u = getattr(m, "usage_metadata", None) or {}
        tok_in += u.get("input_tokens", 0)
        tok_out += u.get("output_tokens", 0)
        cost += (u.get("input_tokens", 0) * PRICE_IN
                 + u.get("output_tokens", 0) * PRICE_OUT)

    print(f"\n{'=' * 50}")
    print(f"步数 {steps} | 消息 {len(final['messages'])} 条 | "
          f"token 入 {tok_in:,} 出 {tok_out:,} | 累计 ${cost:.4f}")
    for i, m in enumerate(final["messages"]):
        kind = type(m).__name__.replace("Message", "")
        tag = ""
        if getattr(m, "tool_calls", None):
            tag = " 🔧" + m.tool_calls[0]["name"]
        if getattr(m, "tool_call_id", None):
            tag = " ↩" + m.tool_call_id
        print(f"  [{i}] {kind:<7}{tag:<10} {str(m.content)[:46]!r}")
