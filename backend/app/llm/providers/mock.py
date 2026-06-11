"""Mock 供应商：不调用任何外部服务，从切片文本中机械生成示例题。

用途：未配置 API Key 时跑通全流程（上传→生成→审核→导出）做演示和测试。
生成的题目质量不代表真实模型水平，题干会标注 [示例] 前缀。
"""
import json
import re

from ..base import LLMProvider


class MockProvider(LLMProvider):
    name = "mock"

    def complete(self, system: str, user: str) -> tuple[str, dict]:
        # 从 user prompt 中提取原文和要求的题型数量
        m = re.search(r"【原文开始】\n(.*?)\n【原文结束】", user, re.S)
        text = m.group(1) if m else user
        sentences = [s.strip() for s in re.split(r"[。\n！？]", text) if len(s.strip()) >= 8][:10]
        if not sentences:
            sentences = ["本段资料内容较短，无法提取要点"]

        counts: dict[str, int] = {}
        for qt, n in re.findall(r"(单选题|多选题|判断题|填空题|简答题|论述题)\s*(\d+)\s*道", user):
            counts[qt] = int(n)
        if not counts:
            counts = {"单选题": 1}

        type_map = {"单选题": "single", "多选题": "multiple", "判断题": "judge",
                    "填空题": "fill_blank", "简答题": "short_answer", "论述题": "essay"}
        questions = []
        si = 0
        for label, n in counts.items():
            qt = type_map[label]
            for _ in range(n):
                s = sentences[si % len(sentences)]
                si += 1
                q: dict = {"q_type": qt, "analysis": f"[示例题] 依据原文：{s[:50]}", "difficulty": "medium"}
                if qt == "single":
                    q["stem"] = f"[示例] 根据资料，下列关于“{s[:20]}”的说法正确的是？"
                    q["options"] = [
                        {"key": "A", "text": s[:40]},
                        {"key": "B", "text": "与原文不符的说法一"},
                        {"key": "C", "text": "与原文不符的说法二"},
                        {"key": "D", "text": "与原文不符的说法三"},
                    ]
                    q["answer"] = "A"
                elif qt == "multiple":
                    q["stem"] = f"[示例] 资料中与“{s[:20]}”相关的正确表述包括哪些？"
                    q["options"] = [
                        {"key": "A", "text": s[:40]},
                        {"key": "B", "text": (sentences[si % len(sentences)])[:40]},
                        {"key": "C", "text": "与原文不符的说法一"},
                        {"key": "D", "text": "与原文不符的说法二"},
                    ]
                    q["answer"] = "AB"
                elif qt == "judge":
                    q["stem"] = f"[示例] {s}。"
                    q["options"] = [{"key": "A", "text": "正确"}, {"key": "B", "text": "错误"}]
                    q["answer"] = "A"
                elif qt == "fill_blank":
                    words = s[: max(4, len(s) // 3)]
                    q["stem"] = f"[示例] {s.replace(words, '_______', 1)}"
                    q["options"] = [{"key": "A", "text": words}]
                    q["answer"] = "A"
                else:  # short_answer / essay
                    q["stem"] = f"[示例] 请结合资料，简述“{s[:25]}”的要点。"
                    q["options"] = None
                    q["answer"] = s
                questions.append(q)
        return json.dumps({"questions": questions}, ensure_ascii=False), {"prompt_tokens": 0, "completion_tokens": 0}
