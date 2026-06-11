import sqlite3
import sys

sys.stdout.reconfigure(encoding="utf-8")
con = sqlite3.connect(r"D:\OpenClaw\CC\AIQS Hub\backend\aiqs.db")
print("=== 任务3 ===")
for row in con.execute("SELECT id, status, model_name, error_msg FROM generation_tasks WHERE id=3"):
    print(row)
print("\n=== 任务3 的模型调用日志 ===")
for row in con.execute(
        "SELECT id, provider, model, latency_ms, success, error_msg FROM llm_call_logs "
        "WHERE task_id=3 ORDER BY id"):
    print(row)
print("\n=== 当前模型配置 ===")
for row in con.execute("SELECT key, value FROM app_settings"):
    k, v = row
    if k == "llm_api_key":
        v = v[:8] + "****"
    print(k, "=", v)
