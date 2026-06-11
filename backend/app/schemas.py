from datetime import datetime

from pydantic import BaseModel, Field

Q_TYPES = ["single", "multiple", "judge", "fill_blank", "short_answer", "essay"]
Q_TYPE_LABELS = {
    "single": "单选",
    "multiple": "多选",
    "judge": "判断题",
    "fill_blank": "填空题",
    "short_answer": "简答题",
    "essay": "论述题",
}
# 题库大类（可在前端选择，questions.category 实际为自由文本，便于扩展）。
# 清单来自配置，部署方可用环境变量 CATEGORIES / SUBCATEGORIES_JSON 覆盖。
from .config import settings  # noqa: E402

CATEGORIES = settings.category_list()
# 大类对应的小类建议（仅作前端提示，小类可填可不填、可自定义）
SUBCATEGORY_SUGGESTIONS = settings.subcategory_map()

# 导出到组卷系统模板时的题型映射（简答/论述 → 主观题）
EXPORT_TYPE_LABELS = {
    "single": "单选",
    "multiple": "多选",
    "judge": "判断题",
    "fill_blank": "填空题",
    "short_answer": "主观题",
    "essay": "主观题",
}


class LoginIn(BaseModel):
    username: str
    password: str


class TokenOut(BaseModel):
    token: str
    username: str
    display_name: str
    role: str


class DocumentOut(BaseModel):
    id: int
    filename: str
    file_type: str
    file_size: int
    parse_status: str
    parse_error: str | None
    chunk_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class ChunkOut(BaseModel):
    id: int
    chunk_index: int
    content: str
    source_locator: str
    char_count: int

    class Config:
        from_attributes = True


class TaskCreateIn(BaseModel):
    document_id: int
    type_counts: dict[str, int] = Field(default_factory=dict)  # {"single": 5, "judge": 3}
    difficulty: str = "medium"
    category: str = ""        # 该资料的大类，生成的题目继承
    subcategory: str = ""     # 小类，可空


class TaskOut(BaseModel):
    id: int
    document_id: int
    config: dict
    model_name: str
    status: str
    error_msg: str | None
    question_count: int
    created_at: datetime
    finished_at: datetime | None

    class Config:
        from_attributes = True


class OptionItem(BaseModel):
    key: str
    text: str


class QuestionOut(BaseModel):
    id: int
    task_id: int | None
    document_id: int | None
    chunk_id: int | None
    q_type: str
    stem: str
    options: list[OptionItem] | None
    answer: str
    analysis: str
    difficulty: str
    category: str
    subcategory: str
    tags: str
    status: str
    reject_reason: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class QuestionUpdateIn(BaseModel):
    stem: str | None = None
    options: list[OptionItem] | None = None
    answer: str | None = None
    analysis: str | None = None
    difficulty: str | None = None
    category: str | None = None
    subcategory: str | None = None
    tags: str | None = None
    q_type: str | None = None


class RejectIn(BaseModel):
    reason: str = ""


class BatchReviewIn(BaseModel):
    ids: list[int]
    action: str  # approve / reject
    reason: str = ""


class ExportIn(BaseModel):
    q_types: list[str] | None = None
    document_id: int | None = None
    keyword: str | None = None
    ids: list[int] | None = None  # 指定题目导出，优先于其他条件


class ModelSettingsIn(BaseModel):
    llm_provider: str
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = ""
    intranet_only: bool = False
