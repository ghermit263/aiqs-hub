import sys

import httpx

sys.stdout.reconfigure(encoding="utf-8")
B = "http://127.0.0.1:8000/api/v1"
c = httpx.Client(timeout=30)
c.headers["Authorization"] = f"Bearer {c.post(f'{B}/auth/login', json={'username': 'admin', 'password': 'admin123'}).json()['token']}"
print("GET theme:", c.get(f"{B}/settings/theme").json())
print("PUT tang:", c.put(f"{B}/settings/theme", json={"skin": "tang"}).json())
print("GET theme:", c.get(f"{B}/settings/theme").json())
print("PUT bad ->", c.put(f"{B}/settings/theme", json={"skin": "x"}).status_code)
c.put(f"{B}/settings/theme", json={"skin": "song"})
print("reset to song:", c.get(f"{B}/settings/theme").json())
