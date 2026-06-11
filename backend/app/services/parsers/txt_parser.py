from pathlib import Path


def parse_txt(file_path: str) -> list[tuple[str, str]]:
    raw = Path(file_path).read_bytes()
    text = None
    for enc in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        raise ValueError("无法识别文本编码，请将文件另存为 UTF-8 或 GBK 编码")
    text = text.strip()
    if not text:
        raise ValueError("文本文件为空")
    # 按空行分块，保留行号定位
    segments: list[tuple[str, str]] = []
    lines = text.splitlines()
    buf: list[str] = []
    start_line = 1
    for i, line in enumerate(lines, start=1):
        if line.strip():
            if not buf:
                start_line = i
            buf.append(line.rstrip())
        elif buf:
            segments.append((f"第{start_line}-{start_line + len(buf) - 1}行", "\n".join(buf)))
            buf = []
    if buf:
        segments.append((f"第{start_line}-{start_line + len(buf) - 1}行", "\n".join(buf)))
    return segments
