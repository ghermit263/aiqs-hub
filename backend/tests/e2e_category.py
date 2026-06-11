# 分类 + 组卷草稿/换题/定稿 端到端测试
import io
import sys
import zipfile

import httpx
from docx import Document

sys.stdout.reconfigure(encoding="utf-8")
BASE = "http://127.0.0.1:8000/api/v1"


def doc_text(data: bytes) -> str:
    from docx.table import Table
    from docx.text.paragraph import Paragraph
    doc = Document(io.BytesIO(data))
    parts = []
    for child in doc.element.body.iterchildren():
        if child.tag.endswith("}p"):
            parts.append(Paragraph(child, doc).text)
        elif child.tag.endswith("}tbl"):
            for row in Table(child, doc).rows:
                parts.append("|".join(c.text for c in row.cells))
    return "\n".join(parts)


def main():
    c = httpx.Client(timeout=120)
    r = c.post(f"{BASE}/auth/login", json={"username": "admin", "password": "admin123"})
    c.headers["Authorization"] = f"Bearer {r.json()['token']}"

    cats = c.get(f"{BASE}/categories").json()
    assert "战略" in cats["categories"] and "内部知识" in cats["categories"]
    assert "党建综合" in cats["subcategories"]["内部知识"]
    print("1. 分类清单 OK:", cats["categories"])

    # 给已有题目打标分类（取若干 approved 题，分别设为不同大类）
    qs = c.get(f"{BASE}/questions", params={"status": "approved", "page_size": 100}).json()["items"]
    assert len(qs) >= 4, f"已审核题不足，当前 {len(qs)}"
    assign = ["战略", "战略", "党建廉洁", "企业文化", "内部知识"]
    for i, q in enumerate(qs):
        cat = assign[i % len(assign)]
        sub = "党建综合" if cat == "内部知识" else ""
        r = c.put(f"{BASE}/questions/{q['id']}", json={"category": cat, "subcategory": sub})
        assert r.status_code == 200, r.text
    print(f"2. 已为 {len(qs)} 道题打标大类")

    # 按大类筛选
    r = c.get(f"{BASE}/questions", params={"status": "approved", "category": "战略", "page_size": 50}).json()
    assert r["total"] >= 1 and all(it["category"] == "战略" for it in r["items"])
    print(f"3. 按大类筛选 OK：战略 {r['total']} 题")

    # 库存按题型×大类
    st = c.get(f"{BASE}/papers/stock").json()
    print("4. 库存（题型→大类分布）:", {k: v for k, v in st.items()})

    # 组卷草稿：单选(战略) + 判断(不限)
    single_strategy = st.get("single", {}).get("战略", 0)
    crit = []
    if single_strategy:
        crit.append({"q_type": "single", "category": "战略", "difficulty": "any",
                     "count": min(single_strategy, 2), "score": 1})
    judge_n = st.get("judge", {}).get("any", 0)
    if judge_n:
        crit.append({"q_type": "judge", "category": "any", "difficulty": "any",
                     "count": min(judge_n, 1), "score": 1})
    assert crit
    d = c.post(f"{BASE}/papers/draft", json={"criteria": crit}).json()
    print(f"5. 草稿 OK：{d['total_questions']} 题，大类分布={d['category_summary']}")
    single_sec = next(s for s in d["sections"] if s["q_type"] == "single")
    assert all(q["category"] == "战略" for q in single_sec["questions"]), "战略条件抽出了非战略题"

    # 换题：给单选第一题找替代
    used_ids = [q["id"] for sec in d["sections"] for q in sec["questions"]]
    orig = single_sec["questions"][0]
    alts = c.get(f"{BASE}/papers/alternatives", params={
        "q_type": "single", "category": "战略", "difficulty": "any",
        "exclude": ",".join(map(str, used_ids))}).json()
    print(f"6. 换题候选 OK：找到 {len(alts)} 道可替换的战略单选题")
    if alts:
        single_sec["questions"][0] = {**alts[0], "score": orig["score"]}
        print(f"   将题 #{orig['id']} 换为 #{alts[0]['id']}")

    # 定稿出卷
    sections_payload = [{"q_type": s["q_type"], "score": s["questions"][0]["score"],
                         "question_ids": [q["id"] for q in s["questions"]]}
                        for s in d["sections"]]
    r = c.post(f"{BASE}/papers", json={"title": "分类组卷测试", "venue": "第二考场",
                                       "sections": sections_payload})
    assert r.status_code == 200, r.text
    info = r.json()
    print(f"7. 定稿出卷 OK：{info['question_count']} 题，满分 {info['total_score']}，大类分布={info['category_distribution']}")

    z = zipfile.ZipFile(io.BytesIO(c.get(f"{BASE}{info['download_url'].removeprefix('/api/v1')}").content))
    assert len(z.namelist()) == 5
    paper_a = doc_text(z.read([n for n in z.namelist() if n.startswith("试卷A")][0]))
    assert "《分类组卷测试》" in paper_a and "（第二考场）" in paper_a
    print("8. zip 5 个 docx OK，试卷版式正常")
    print("\n=== 分类 + 组卷微调 全部测试通过 ===")


if __name__ == "__main__":
    main()
