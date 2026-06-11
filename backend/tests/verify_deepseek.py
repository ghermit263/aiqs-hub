# 验证 DeepSeek 修复：测试连接 → 对愿景txt重跑小任务 → 查看生成题目与日志
import sys
import time

import httpx

sys.stdout.reconfigure(encoding="utf-8")
BASE = "http://127.0.0.1:8000/api/v1"

c = httpx.Client(timeout=300)
r = c.post(f"{BASE}/auth/login", json={"username": "admin", "password": "admin123"})
c.headers["Authorization"] = f"Bearer {r.json()['token']}"

# 1. 测试连接
r = c.post(f"{BASE}/settings/models/test")
info = r.json()
assert info["ok"], f"连接测试失败: {info.get('error')}"
print(f"1. 连接测试 OK：{info['provider']}:{info['model']} {info['latency_ms']}ms 回复={info['reply']!r}")

# 2. 找到愿景 txt 资料
docs = c.get(f"{BASE}/documents").json()
doc = next(d for d in docs if d["filename"].endswith(".txt") and "愿景" in d["filename"])
print(f"2. 资料: #{doc['id']} {doc['filename']} 切片={doc['chunk_count']}")

# 3. 小批量重跑（单选2+判断1，控制 token 消耗）
r = c.post(f"{BASE}/tasks", json={"document_id": doc["id"],
                                  "type_counts": {"single": 2, "judge": 1},
                                  "difficulty": "medium"})
task_id = r.json()["id"]
print(f"3. 任务 #{task_id} 已提交，等待 DeepSeek 出题...")
for _ in range(120):
    time.sleep(2)
    t = c.get(f"{BASE}/tasks/{task_id}").json()
    if t["status"] in ("done", "failed"):
        break
assert t["status"] == "done", f"任务失败: {t['error_msg']}"
print(f"4. 生成成功：{t['question_count']} 题，模型={t['model_name']}")
if t["error_msg"]:
    print("   （部分警告）", t["error_msg"][:150])

# 4. 展示生成的题目
qs = c.get(f"{BASE}/questions", params={"status": "pending_review", "document_id": doc["id"],
                                        "page_size": 10}).json()
for q in qs["items"]:
    print(f"\n  [{q['q_type']}] {q['stem']}")
    for o in (q["options"] or []):
        print(f"    {o['key']}. {o['text']}")
    print(f"    答案: {q['answer']}  解析: {q['analysis'][:60]}")

# 5. 日志接口
logs = c.get(f"{BASE}/settings/llm-logs", params={"limit": 5}).json()
print(f"\n5. 调用日志 OK（最近{len(logs)}条），最新一条: success={logs[0]['success']} {logs[0]['latency_ms']}ms")
applog = c.get(f"{BASE}/settings/app-log").json()
print(f"6. 运行日志 OK（{len(applog['lines'])}行），末行: {applog['lines'][-1] if applog['lines'] else '空'}")
print("\n=== DeepSeek 出题链路验证通过 ===")
