# 组卷模块端到端测试：库存查询→组卷→下载zip→解析docx校验AB卷乱序与答案映射
import io
import sys
import zipfile

import httpx
from docx import Document

sys.stdout.reconfigure(encoding="utf-8")
BASE = "http://127.0.0.1:8000/api/v1"


def doc_text(data: bytes) -> str:
    """按文档真实顺序提取段落与表格文本。"""
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

    stock = c.get(f"{BASE}/papers/stock").json()
    print("1. 库存:", {k: v["any"] for k, v in stock.items()})

    # 按库存构造组卷条件（mock 题库较小）
    criteria = []
    for q_type, per_score in (("single", 1), ("multiple", 2), ("judge", 1), ("short_answer", 8)):
        n = stock.get(q_type, {}).get("any", 0)
        if n:
            criteria.append({"q_type": q_type, "difficulty": "any", "count": min(n, 3), "score": per_score})
    assert criteria, "题库为空，无法测试"

    # 超量应报错
    r = c.post(f"{BASE}/papers", json={"title": "超量测试", "venue": "", "criteria": [
        {"q_type": "single", "difficulty": "any", "count": 99, "score": 1}]})
    assert r.status_code == 400 and "不足" in r.json()["detail"], r.text
    print("2. 题库不足校验 OK:", r.json()["detail"][:40])

    r = c.post(f"{BASE}/papers", json={
        "title": "数智化转型专项考试", "venue": "第一考场", "criteria": criteria})
    assert r.status_code == 200, r.text
    info = r.json()
    print(f"3. 组卷 OK：{info['question_count']} 题，满分 {info['total_score']} 分")

    r = c.get(f"{BASE}{info['download_url'].removeprefix('/api/v1')}")
    assert r.status_code == 200
    zf = zipfile.ZipFile(io.BytesIO(r.content))
    names = zf.namelist()
    assert len(names) == 5, names
    print("4. zip 包 OK:", names)

    paper_a = doc_text(zf.read([n for n in names if n.startswith("试卷A")][0]))
    paper_b = doc_text(zf.read([n for n in names if n.startswith("试卷B")][0]))
    key = doc_text(zf.read([n for n in names if n.startswith("参考答案")][0]))
    sheet_a = doc_text(zf.read([n for n in names if n.startswith("答题卡A")][0]))

    # 卷面要素
    for must in ("《数智化转型专项考试》", "试卷（A）", "（第一考场）", "姓  名", "员工编号",
                 "题目必须在答题纸上作答"):
        assert must in paper_a, f"试卷A缺少: {must}"
    assert "一、单选题" in paper_a and "每题1分" in paper_a
    print("5. 试卷版式 OK（封面/信息表/警示语/节标题/分值）")

    # AB 卷乱序：题面集合相同、顺序或选项排列不同
    assert paper_a != paper_b, "AB卷内容完全相同，乱序未生效"
    print("6. AB 卷乱序 OK（卷面内容不同）")

    # 答案映射正确性：从题库取原题，对照试卷A中该题的选项排列和参考答案
    qs = c.get(f"{BASE}/questions", params={"status": "approved", "q_type": "single",
                                            "page_size": 50}).json()["items"]
    import re
    checked = 0
    for orig in qs:
        stem_key = orig["stem"][:25]
        if stem_key not in paper_a:
            continue
        # 在试卷A中找到该题的编号与选项
        m = re.search(rf"(\d+)\.[^\n]*{re.escape(stem_key)}", paper_a)
        if not m:
            continue
        no = m.group(1)
        opts: dict[str, str] = {}
        for line in paper_a[m.end():].split("\n"):
            om = re.match(r"^([A-D])\.(.+)$", line.strip())
            if om:
                opts[om.group(1)] = om.group(2)
            elif re.match(r"^\d+\.", line.strip()) or line.strip().startswith(("一、", "二、", "三、", "四、")):
                break  # 到下一题/下一节为止
        correct_text = next(o["text"] for o in orig["options"] if o["key"] == orig["answer"])
        # 参考答案里查 A 卷单选题小节内该题号的答案字母
        ka = key[key.index("试卷（A）"):key.index("试卷（B）")]
        ka_single = ka[ka.index("一、单选题"):]
        nxt = re.search(r"\n[二三四五六]、", ka_single)
        if nxt:
            ka_single = ka_single[:nxt.start()]
        rows = re.findall(r"题号\|([\d|]+)\n答案\|([A-D√×|]+)", ka_single)
        ans_letter = None
        for nos, answers in rows:
            nlist, alist = nos.split("|"), answers.split("|")
            if no in nlist:
                ans_letter = alist[nlist.index(no)]
        assert ans_letter, f"参考答案中找不到题号{no}"
        assert opts.get(ans_letter, "").strip() == correct_text.strip(), (
            f"答案映射错误: 题{no} 参考答案{ans_letter}={opts.get(ans_letter)} 应为 {correct_text}")
        checked += 1
    assert checked > 0, "未能校验到任何单选题映射"
    print(f"7. 选项乱序后答案映射 OK（抽查 {checked} 道单选题，全部正确）")

    assert "答 题 纸" in sheet_a and "题号" in sheet_a
    print("8. 答题卡 OK（题号/答案表格）")

    print("\n=== 组卷模块全部测试通过 ===")


if __name__ == "__main__":
    main()
