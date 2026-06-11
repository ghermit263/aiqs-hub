"""文档解析器：每种格式返回 [(source_locator, text), ...] 片段列表。"""
from pathlib import Path

from .pdf import parse_pdf
from .docx_parser import parse_docx
from .pptx_parser import parse_pptx
from .xlsx_parser import parse_xlsx
from .txt_parser import parse_txt
from .image_parser import parse_image

PARSERS = {
    "pdf": parse_pdf,
    "docx": parse_docx,
    "doc": parse_docx,
    "pptx": parse_pptx,
    "ppt": parse_pptx,
    "xlsx": parse_xlsx,
    "xls": parse_xlsx,
    "txt": parse_txt,
    "jpg": parse_image,
    "jpeg": parse_image,
    "png": parse_image,
}

SUPPORTED_EXTS = set(PARSERS)


def parse_file(file_path: str, file_type: str) -> list[tuple[str, str]]:
    parser = PARSERS.get(file_type)
    if not parser:
        raise ValueError(f"不支持的文件类型: {file_type}")
    if not Path(file_path).exists():
        raise FileNotFoundError(file_path)
    return parser(file_path)
