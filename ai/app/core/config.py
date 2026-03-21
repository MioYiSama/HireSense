from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent

CHROMA_DATA = BASE_DIR/"chroma_db_data"
NEO4J_DATA  = BASE_DIR/"neo4j_data"
EMBEDDING_MODEL = BASE_DIR/"Embedding_model"/"bge-m3"
BGE_RERANKER = BASE_DIR/"Score_model"/"BAAI"/"bge-reranker-v2-m3"
NLI          = BASE_DIR/"Score_model"/"MoritzLaurer"/"mDeBERTa-v3-base-mnli-xnli"
RECOMMEND_DATA = BASE_DIR/"data_source"/"recommend_data.json"
ENV_FILE_PATH  = BASE_DIR/".env"


class Settings(BaseSettings):
    # ... (原有字段定义保持不变) ...
    LLM_API_KEY: str
    LLM_BASE_URL: str
    FAST_LLM_MODEL: str = "qwen-turbo"
    SMART_LLM_MODEL: str = "qwen-max"
    REPORT_LLM_MODEL: str = "qwen-plus"
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str
    CHROMA_PERSIST_DIR: str = "./chroma_db_data"
    TARGET_SERVER_URL: str
    INTERNAL_SECRET: str

    # ==========================================
    # 强制 Pydantic 读取绝对路径的 .env
    # ==========================================
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE_PATH), # <--- 传入绝对路径字符串
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
