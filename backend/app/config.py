from pathlib import Path

from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent  # backend/
STORAGE_DIR = BASE_DIR / "storage"
UPLOAD_DIR = STORAGE_DIR / "uploads"
EXPORT_DIR = STORAGE_DIR / "exports"


class Settings(BaseSettings):
    app_name: str = "AIQS Hub 智能题源中心"
    database_url: str = f"sqlite:///{BASE_DIR / 'aiqs.db'}"
    jwt_secret: str = "change-me-in-production"
    jwt_expire_minutes: int = 12 * 60

    # model gateway 默认配置（可被数据库 settings 表覆盖）
    llm_provider: str = "mock"  # mock / openai_compat / claude
    llm_base_url: str = ""      # openai_compat 时必填，如 https://api.deepseek.com/v1
    llm_api_key: str = ""
    llm_model: str = ""
    llm_timeout: int = 180
    intranet_only: bool = False  # 内网模式：禁止调用外部 API

    max_upload_mb: int = 100
    chunk_size: int = 1200      # 切片目标字数
    chunk_min_size: int = 200   # 小于此值的尾片并入前一片

    # 题库大类清单（逗号分隔）。公开版为通用示例，部署方可在 .env 用 CATEGORIES 覆盖为本单位分类。
    categories: str = "公共基础,专业知识,法律法规,安全生产,业务技能,管理知识"
    # 大类→建议小类，JSON 字符串，如 {"专业知识": ["网络技术", "业务服务"]}
    subcategories_json: str = "{}"

    def category_list(self) -> list[str]:
        return [c.strip() for c in self.categories.split(",") if c.strip()]

    def subcategory_map(self) -> dict[str, list[str]]:
        import json
        try:
            return json.loads(self.subcategories_json or "{}")
        except json.JSONDecodeError:
            return {}

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
EXPORT_DIR.mkdir(parents=True, exist_ok=True)
