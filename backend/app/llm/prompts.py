"""出题 prompt 模板。"""

SYSTEM_PROMPT = """你是一名企业培训考试命题专家。你的任务是严格依据给定的资料原文出题，不允许编造资料中不存在的内容。

出题要求：
1. 题目必须能从原文中找到依据，解析中要引用原文关键句。
2. 单选题4个选项有且仅有1个正确；多选题4个选项中2-3个正确；干扰项要合理（似是而非），不要明显荒谬。
3. 判断题选项固定为 A=正确、B=错误，答案填 A 或 B。
4. 填空题题干中用 _______ 表示空位，每个空的答案依次放入 options 的 A、B…，answer 填所用选项字母如 "AB"。
5. 简答题/论述题不设选项（options 为 null），answer 为参考答案要点。
6. 题干表述完整独立，不出现"根据本段""上文中"等依赖上下文的措辞。

输出格式：只输出一个 JSON 对象，不要任何其他文字，结构如下：
{"questions": [{"q_type": "single|multiple|judge|fill_blank|short_answer|essay", "stem": "题干", "options": [{"key": "A", "text": "..."}] 或 null, "answer": "A", "analysis": "解析（含原文依据）", "difficulty": "easy|medium|hard"}]}"""

TYPE_LABELS = {
    "single": "单选题",
    "multiple": "多选题",
    "judge": "判断题",
    "fill_blank": "填空题",
    "short_answer": "简答题",
    "essay": "论述题",
}

DIFFICULTY_LABELS = {"easy": "简单", "medium": "中等", "hard": "困难"}


def build_user_prompt(chunk_text: str, source_locator: str, type_counts: dict[str, int],
                      difficulty: str = "medium") -> str:
    req_lines = [f"- {TYPE_LABELS[t]} {n} 道" for t, n in type_counts.items() if n > 0 and t in TYPE_LABELS]
    return f"""请依据以下资料原文出题（来源位置：{source_locator}）。

【原文开始】
{chunk_text}
【原文结束】

请生成：
{chr(10).join(req_lines)}

整体难度：{DIFFICULTY_LABELS.get(difficulty, '中等')}。
若原文信息量不足以支撑要求的题量，宁可少出，不要编造。只输出 JSON。"""
