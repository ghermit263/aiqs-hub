"""图片 OCR 解析：RapidOCR（本地 ONNX 推理，不依赖外部服务，适合内网敏感资料）。

rapidocr_onnxruntime 为可选依赖，未安装时给出明确提示。
模型首次加载约 1-2 秒，进程内复用单例。
"""
_ocr_engine = None


def _get_engine():
    global _ocr_engine
    if _ocr_engine is None:
        try:
            from rapidocr_onnxruntime import RapidOCR
        except ImportError:
            raise ValueError(
                "未安装 OCR 组件，无法识别图片。请执行: "
                "pip install rapidocr_onnxruntime -i https://pypi.tuna.tsinghua.edu.cn/simple"
            )
        _ocr_engine = RapidOCR()
    return _ocr_engine


def parse_image(file_path: str) -> list[tuple[str, str]]:
    engine = _get_engine()
    result, _ = engine(file_path)
    if not result:
        raise ValueError("OCR 未能从图片中识别出任何文字，请确认图片清晰且包含文字")
    # result: [[box, text, score], ...]，按识别顺序拼接，过滤低置信度
    lines = [item[1] for item in result if len(item) >= 3 and float(item[2]) >= 0.5]
    if not lines:
        raise ValueError("图片文字识别置信度过低，请上传更清晰的图片")
    return [("图片OCR", "\n".join(lines))]
