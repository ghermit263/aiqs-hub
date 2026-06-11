import openpyxl


def parse_xlsx(file_path: str) -> list[tuple[str, str]]:
    if file_path.lower().endswith(".xls"):
        raise ValueError("暂不支持旧版 .xls，请先在 Excel 中另存为 .xlsx")
    wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
    segments: list[tuple[str, str]] = []
    for ws in wb.worksheets:
        rows: list[str] = []
        start_row = None
        for r_idx, row in enumerate(ws.iter_rows(values_only=True), start=1):
            cells = [str(c).strip() for c in row if c is not None and str(c).strip()]
            if not cells:
                continue
            if start_row is None:
                start_row = r_idx
            rows.append(" | ".join(cells))
            # 每 40 行成一段，避免单段过大
            if len(rows) >= 40:
                segments.append((f"{ws.title}!第{start_row}-{r_idx}行", "\n".join(rows)))
                rows, start_row = [], None
        if rows:
            segments.append((f"{ws.title}!第{start_row}行起", "\n".join(rows)))
    wb.close()
    return segments
