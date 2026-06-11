"""把解析出的 (locator, text) 片段切成适合送给大模型的切片。

策略：以解析片段为基本单位（保持来源定位准确），过长的片段在段落/句子边界二分，
过短的相邻片段（同一 locator 前缀）不合并——宁可多切，保证溯源不串页。
"""
import re

from ..config import settings


def _split_long(text: str, limit: int) -> list[str]:
    if len(text) <= limit:
        return [text]
    # 优先按空行，再按换行，再按句号切
    for sep_pattern in (r"\n\s*\n", r"\n", r"(?<=[。！？；])"):
        parts = [p for p in re.split(sep_pattern, text) if p and p.strip()]
        if len(parts) > 1:
            chunks: list[str] = []
            buf = ""
            for p in parts:
                if buf and len(buf) + len(p) > limit:
                    chunks.append(buf)
                    buf = p
                else:
                    buf = f"{buf}\n{p}" if buf else p
            if buf:
                chunks.append(buf)
            # 递归处理仍然超长的块（如无标点长文本）
            result: list[str] = []
            for c in chunks:
                if len(c) > limit * 1.5:
                    result.extend(c[i : i + limit] for i in range(0, len(c), limit))
                else:
                    result.append(c)
            return result
    return [text[i : i + limit] for i in range(0, len(text), limit)]


def chunk_segments(segments: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """返回 [(source_locator, chunk_text), ...]"""
    limit = settings.chunk_size
    out: list[tuple[str, str]] = []
    for locator, text in segments:
        text = text.strip()
        if not text:
            continue
        pieces = _split_long(text, limit)
        # 尾片太短则并回前一片
        if len(pieces) > 1 and len(pieces[-1]) < settings.chunk_min_size:
            pieces[-2] = pieces[-2] + "\n" + pieces[-1]
            pieces.pop()
        if len(pieces) == 1:
            out.append((locator, pieces[0]))
        else:
            for i, p in enumerate(pieces, start=1):
                out.append((f"{locator}({i}/{len(pieces)})", p))
    return out
