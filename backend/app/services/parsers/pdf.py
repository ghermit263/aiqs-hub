import fitz  # PyMuPDF


def parse_pdf(file_path: str) -> list[tuple[str, str]]:
    segments: list[tuple[str, str]] = []
    with fitz.open(file_path) as doc:
        empty_pages = 0
        for i, page in enumerate(doc, start=1):
            text = page.get_text("text").strip()
            if text:
                segments.append((f"第{i}页", text))
            else:
                empty_pages += 1
        if not segments and empty_pages:
            raise ValueError("未能从 PDF 提取到文本，可能是扫描件，需要先做 OCR")
    return segments
