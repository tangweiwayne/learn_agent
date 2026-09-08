"""演示：当模型敲出危险命令时，确认闸门长什么样。

用法：
    python3 demo_confirm.py          # 真的问你 y/n
    echo "y
n
y" | python3 demo_confirm.py         # 预先喂答案（演示用）
"""
from v2_agent import build_agent
from v2_confirm import ConfirmAgent
from v2_model import MockModel

# 一个会敲危险命令的假模型
危险台词 = [
    "先看看有什么文件。\n\n```bash\nls\n```",
    "我来把 a.py 改一下。\n\n```bash\nsed -i 's/old/new/' a.py\n```",
    "顺手清理一下临时文件。\n\n```bash\nrm -f readme.txt\n```",
    "装个依赖。\n\n```bash\npip install requests\n```",
    "好了，完成。\n\n```bash\necho TASK_DONE\n```",
]

agent = build_agent(mock=True, agent_class=ConfirmAgent)
agent.model = MockModel(scripted=危险台词)
agent.run("演示确认功能")

print("\n" + "=" * 50)
print(f"步数 {agent.step_count} | 你拒绝了 {agent.rejected} 条命令")
