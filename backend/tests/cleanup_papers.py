import sqlite3
from pathlib import Path

con = sqlite3.connect(r"D:\OpenClaw\CC\AIQS Hub\backend\aiqs.db")
rows = con.execute("SELECT id, file_path FROM papers ORDER BY id DESC").fetchall()
for pid, fp in rows[1:]:  # 保留最新一份
    Path(fp).unlink(missing_ok=True)
    con.execute("DELETE FROM papers WHERE id = ?", (pid,))
con.commit()
print(f"kept latest, removed {len(rows) - 1}")
