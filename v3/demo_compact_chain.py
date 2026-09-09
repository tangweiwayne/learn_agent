"""跑一遍现在的压缩链：Agent.compact() → for_api()，看每条消息的变化。"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v3_model import for_api

TRACE = sys.argv[1] if len(sys.argv) > 1 else "traces/0909_141440.json"

messages = json.load(open(TRACE))["messages"]


class FakeAgent:
    compact_keep_steps = 3
    compact_min_chars = 800


from v3_agent import Agent
compact = Agent.compact.__get__(FakeAgent())      # 借用真函数，不用建整个 Agent

sent = compact(messages)
payload = for_api(sent)


def size(m):
    return len(str(m.get("content") or ""))


print(f"{'':4} {'role':10} {'原始':>7} {'compact后':>9} {'for_api后':>9}  keys 变化")
print("-" * 72)
for i, (a, b, c) in enumerate(zip(messages, sent, payload)):
    mark = "✂" if size(a) != size(b) else " "
    dropped = sorted(set(a.keys()) - set(c.keys()))
    print(f"{mark}[{i:2}] {a['role']:10} {size(a):7} {size(b):9} {len(c['content']):9}  "
          f"{'-' + ','.join(dropped) if dropped else ''}")

print("-" * 72)
tot = lambda ms: sum(size(m) for m in ms)
print(f"{'合计':6} {'':8} {tot(messages):7} {tot(sent):9} {tot(payload):9}")
