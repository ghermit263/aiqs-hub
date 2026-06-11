# 测试：批量改分类 / AB可选 / 预览 / 单独docx下载
import io
import sys
import zipfile

import httpx

sys.stdout.reconfigure(encoding="utf-8")
BASE = "http://127.0.0.1:8000/api/v1"


def main():
    c = httpx.Client(timeout=120)
    c.headers["Authorization"] = f"Bearer {c.post(f'{BASE}/auth/login', json={'username':'admin','password':'admin123'}).json()['token']}"

    # 1. 批量改分类
    qs = c.get(f"{BASE}/questions", params={"status": "approved", "page_size": 5}).json()["items"]
    ids = [q["id"] for q in qs[:3]]
    r = c.post(f"{BASE}/questions/batch-category", json={"ids": ids, "category": "管理", "subcategory": "制度"})
    assert r.status_code == 200 and r.json()["count"] == 3, r.text
    check = c.get(f"{BASE}/questions", params={"status": "approved", "category": "管理", "page_size": 50}).json()
    assert all(it["category"] == "管理" for it in check["items"]) and check["total"] >= 3
    assert any(it["subcategory"] == "制度" for it in check["items"])
    print(f"1. 批量改分类 OK：{len(ids)} 题改为 管理/制度，筛选回查 {check['total']} 题")

    # 准备组卷 sections
    st = c.get(f"{BASE}/papers/stock").json()
    sections = []
    for qt in ("single", "judge"):
        n = st.get(qt, {}).get("any", 0)
        if n:
            picks = c.get(f"{BASE}/questions", params={"status": "approved", "q_type": qt, "page_size": 3}).json()["items"]
            sections.append({"q_type": qt, "score": 1, "question_ids": [p["id"] for p in picks[:min(2, n)]]})
    assert sections

    # 2. 预览（不落库）
    r = c.post(f"{BASE}/papers/preview", json={"title": "预览测试", "sections": sections, "versions": ["A", "B"]})
    assert r.status_code == 200, r.text
    pv = r.json()
    assert set(pv["versions"]) == {"A", "B"}
    a_first = pv["preview"]["A"][0]
    assert "questions" in a_first and a_first["questions"][0]["no"] == 1
    assert "answer" in a_first["questions"][0]
    print(f"2. 预览 OK：A/B 两卷，A卷首节 {a_first['label']} {len(a_first['questions'])}题，含题号与答案")

    # 3. 只出 A 卷
    r = c.post(f"{BASE}/papers", json={"title": "仅A卷测试", "venue": "", "sections": sections, "versions": ["A"]})
    assert r.status_code == 200, r.text
    info = r.json()
    assert info["versions"] == ["A"]
    files = info["files"]
    assert any(f.startswith("试卷A") for f in files) and not any(f.startswith("试卷B") for f in files)
    assert any(f.startswith("参考答案") for f in files)
    print(f"3. 仅A卷 OK：生成文件 {files}")
    assert "preview" in info and "A" in info["preview"]
    print("   组卷返回内含预览数据 OK")

    # 4. 单独 docx 下载
    paper_id = info["id"]
    detail = c.get(f"{BASE}/papers/{paper_id}").json()
    assert detail["preview"] and detail["files"], "详情应含预览与文件列表"
    target = [f for f in files if f.startswith("试卷A")][0]
    r = c.get(f"{BASE}/papers/{paper_id}/file", params={"name": target})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/vnd.openxmlformats")
    from docx import Document
    doc = Document(io.BytesIO(r.content))
    assert any("仅A卷测试" in p.text for p in doc.paragraphs)
    print(f"4. 单独 docx 下载 OK：{target}（{len(r.content)} 字节，可直接编辑）")

    # 同时 zip 仍可用
    r = c.get(f"{BASE}/papers/{paper_id}/download")
    z = zipfile.ZipFile(io.BytesIO(r.content))
    assert len(z.namelist()) == len(files)
    print(f"5. zip 整包仍可用 OK（{len(z.namelist())} 个 docx）")

    # AB 双卷
    r = c.post(f"{BASE}/papers", json={"title": "AB双卷测试", "venue": "第一考场", "sections": sections, "versions": ["A", "B"]})
    ab = r.json()
    assert ab["versions"] == ["A", "B"] and len(ab["files"]) == 5
    print(f"6. AB双卷 OK：{ab['files']}")

    print("\n=== 第4轮（批量分类/AB可选/预览/单独docx）全部通过 ===")


if __name__ == "__main__":
    main()
