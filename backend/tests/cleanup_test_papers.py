import sqlite3
from pathlib import Path

con = sqlite3.connect(r"D:\OpenClaw\CC\AIQS Hub\backend\aiqs.db")
rows = con.execute("SELECT id, file_path FROM papers WHERE title LIKE '%测试%'").fetchall()
for pid, fp in rows:
    Path(fp).unlink(missing_ok=True)
    con.execute("DELETE FROM papers WHERE id = ?", (pid,))
con.commit()
print(f"removed {len(rows)} test papers")
