import sqlite3

con = sqlite3.connect(r"D:\OpenClaw\CC\AIQS Hub\backend\aiqs.db")
con.execute("DELETE FROM users WHERE username = 'zhangsan'")
con.commit()
print("cleaned")
