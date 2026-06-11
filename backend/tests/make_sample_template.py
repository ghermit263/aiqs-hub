"""生成开源用的通用导入模板示例（不含任何真实题目）。"""
import openpyxl
from openpyxl.styles import Font

wb = openpyxl.Workbook()
ws = wb.active
ws.title = "试题导入模板"
ws.append(["题干", "类型", "答案", "选项A", "选项B", "选项C", "选项D"])
for cell in ws[1]:
    cell.font = Font(bold=True)
rows = [
    ["示例：以下哪一项属于关系型数据库？", "单选", "A", "MySQL", "Redis", "MongoDB", "Elasticsearch"],
    ["示例：下列属于面向对象三大特性的有？", "多选", "ABC", "封装", "继承", "多态", "编译"],
    ["示例：HTTP 是无状态协议。", "判断题", "A", "正确", "错误", None, None],
    ["示例：TCP/IP 模型分为应用层、传输层、_____、网络接口层。", "填空题", "A", "网络层", None, None, None],
    ["示例：简述什么是幂等性，并举一个例子。", "主观题", "A", "同一操作多次执行结果一致；如 HTTP GET。", None, None, None],
]
for r in rows:
    ws.append(r)
ws.column_dimensions["A"].width = 50
for col in "DEFG":
    ws.column_dimensions[col].width = 22
wb.save(r"D:\OpenClaw\CC\AIQS Hub\templates\sample_import_template.xlsx")
print("sample template created")
