"""按组卷系统导入模板导出 Excel。

模板格式（templates/题库模版.xlsx，Sheet名：试题导入模板）：
  题干 | 类型 | 答案 | 选项A | 选项B | 选项C | 选项D
题型映射：单选/多选/判断题/填空题；简答题、论述题 → 主观题（参考答案放选项A列）。
"""
from datetime import datetime

import openpyxl
from openpyxl.styles import Font

from ..config import EXPORT_DIR
from ..models import Question
from ..schemas import EXPORT_TYPE_LABELS

HEADERS = ["题干", "类型", "答案", "选项A", "选项B", "选项C", "选项D"]
SHEET_NAME = "试题导入模板"


def _question_to_row(q: Question) -> list[str]:
    label = EXPORT_TYPE_LABELS[q.q_type]
    opts = {o["key"]: o["text"] for o in (q.options or [])}
    if q.q_type in ("single", "multiple", "fill_blank"):
        row = [q.stem, label, q.answer,
               opts.get("A", ""), opts.get("B", ""), opts.get("C", ""), opts.get("D", "")]
    elif q.q_type == "judge":
        row = [q.stem, label, q.answer, "正确", "错误", "", ""]
    else:  # short_answer / essay → 主观题，参考答案放选项A
        row = [q.stem, label, "A", q.answer, "", "", ""]
    return row


def export_questions(questions: list[Question]) -> str:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = SHEET_NAME
    ws.append(HEADERS)
    for cell in ws[1]:
        cell.font = Font(bold=True)
    for q in questions:
        ws.append(_question_to_row(q))
    ws.column_dimensions["A"].width = 60
    for col in "DEFG":
        ws.column_dimensions[col].width = 30
    filename = f"题库导出_{datetime.now():%Y%m%d_%H%M%S}.xlsx"
    path = EXPORT_DIR / filename
    wb.save(path)
    return str(path)
