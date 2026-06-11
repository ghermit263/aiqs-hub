# 第二阶段端到端测试：txt/图片OCR上传、注册审批流、角色权限、修改密码
import io
import sys
import time

import httpx

sys.stdout.reconfigure(encoding="utf-8")
BASE = "http://127.0.0.1:8000/api/v1"


def make_test_image() -> bytes:
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new("RGB", (800, 220), "white")
    d = ImageDraw.Draw(img)
    font = ImageFont.truetype(r"C:\Windows\Fonts\simhei.ttf", 32)
    d.text((30, 30), "网络强基全栈创新战略要点", font=font, fill="black")
    d.text((30, 90), "加强智能布局卡位，加快算力市场拓展", font=font, fill="black")
    d.text((30, 150), "夯实通信服务根基，推进数智化转型", font=font, fill="black")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def wait_parse(c, doc_id, n=40):
    for _ in range(n):
        time.sleep(0.5)
        d = c.get(f"{BASE}/documents/{doc_id}").json()
        if d["parse_status"] in ("done", "failed"):
            return d
    return d


def main():
    admin = httpx.Client(timeout=120)
    r = admin.post(f"{BASE}/auth/login", json={"username": "admin", "password": "admin123"})
    assert r.status_code == 200, r.text
    admin.headers["Authorization"] = f"Bearer {r.json()['token']}"
    print("1. admin 登录 OK")

    # txt 上传
    txt = "中国移动数智化转型要点\n\n第一部分：AI First 战略。\n推进大模型在客服、网络运维场景落地。\n\n第二部分：算力网络。\n加快算力市场拓展，建设智算中心。".encode("utf-8")
    r = admin.post(f"{BASE}/documents", files={"file": ("要点.txt", txt, "text/plain")})
    assert r.status_code == 200, r.text
    d = wait_parse(admin, r.json()["id"])
    assert d["parse_status"] == "done", d
    chunks = admin.get(f"{BASE}/documents/{d['id']}/chunks").json()
    print(f"2. txt 解析 OK：{d['chunk_count']} 切片，定位示例: {chunks[0]['source_locator']}")

    # 图片 OCR
    r = admin.post(f"{BASE}/documents", files={"file": ("白板拍照.jpg", make_test_image(), "image/jpeg")})
    assert r.status_code == 200, r.text
    d = wait_parse(admin, r.json()["id"], n=120)  # 首次加载 OCR 模型较慢
    assert d["parse_status"] == "done", d
    chunks = admin.get(f"{BASE}/documents/{d['id']}/chunks").json()
    text = chunks[0]["content"]
    assert "网络强基" in text or "算力" in text, f"OCR 结果异常: {text}"
    print(f"3. 图片 OCR OK：识别内容: {text[:40]}...")

    # 注册 → 待审批不能登录
    r = admin.post(f"{BASE}/auth/register", json={"username": "zhangsan", "password": "pass123456", "display_name": "张三"})
    assert r.status_code == 200, r.text
    r = httpx.post(f"{BASE}/auth/login", json={"username": "zhangsan", "password": "pass123456"})
    assert r.status_code == 403 and "审批" in r.json()["detail"], r.text
    print("4. 注册 OK，待审批状态登录被拒 OK")

    # admin 审批通过
    users = admin.get(f"{BASE}/users").json()
    zs = next(u for u in users if u["username"] == "zhangsan")
    assert zs["status"] == "pending" and zs["role"] == "uploader"
    admin.put(f"{BASE}/users/{zs['id']}", json={"status": "active"})
    up = httpx.Client(timeout=30)
    r = up.post(f"{BASE}/auth/login", json={"username": "zhangsan", "password": "pass123456"})
    assert r.status_code == 200, r.text
    up.headers["Authorization"] = f"Bearer {r.json()['token']}"
    print("5. 审批通过后登录 OK，角色=uploader")

    # 上传人权限边界
    r = up.post(f"{BASE}/tasks", json={"document_id": 1, "type_counts": {"single": 1}})
    assert r.status_code == 403, f"上传人不应能建任务: {r.status_code}"
    r = up.post(f"{BASE}/exports", json={})
    assert r.status_code == 403, f"上传人不应能导出: {r.status_code}"
    r = up.get(f"{BASE}/questions", params={"status": "approved"})
    assert r.status_code == 200, "上传人应能查看题目"
    r = up.get(f"{BASE}/users")
    assert r.status_code == 403, "非管理员不应能看用户列表"
    # 上传人只能删自己的资料
    r = up.delete(f"{BASE}/documents/{d['id']}")  # admin 上传的图片
    assert r.status_code == 403, f"上传人不应能删他人资料: {r.status_code}"
    print("6. 权限边界 OK：建任务403 / 导出403 / 查题200 / 用户管理403 / 删他人资料403")

    # 修改密码
    r = up.post(f"{BASE}/auth/change-password", json={"old_password": "pass123456", "new_password": "newpass789"})
    assert r.status_code == 200, r.text
    r = httpx.post(f"{BASE}/auth/login", json={"username": "zhangsan", "password": "newpass789"})
    assert r.status_code == 200, "新密码应能登录"
    r = httpx.post(f"{BASE}/auth/login", json={"username": "zhangsan", "password": "pass123456"})
    assert r.status_code == 401, "旧密码应失效"
    print("7. 修改密码 OK：新密码可登录，旧密码失效")

    # 停用账号
    admin.put(f"{BASE}/users/{zs['id']}", json={"status": "disabled"})
    r = httpx.post(f"{BASE}/auth/login", json={"username": "zhangsan", "password": "newpass789"})
    assert r.status_code == 403 and "停用" in r.json()["detail"]
    print("8. 停用账号 OK：登录被拒")

    print("\n=== 第二阶段全部测试通过 ===")


if __name__ == "__main__":
    main()
