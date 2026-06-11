import time

import httpx

c = httpx.Client(base_url="http://127.0.0.1:8000/api/v1", timeout=30)
t = c.post("/auth/login", json={"username": "admin", "password": "admin123"}).json()["token"]
c.headers["Authorization"] = f"Bearer {t}"
r = c.post("/tasks", json={"document_id": 1,
                           "type_counts": {"single": 2, "judge": 1, "fill_blank": 1},
                           "difficulty": "medium"}).json()
time.sleep(2)
print(c.get(f"/tasks/{r['id']}").json()["status"])
