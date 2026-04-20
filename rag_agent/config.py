from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # app base settings
    APP_NAME: str = "RAG Agent"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # db
    DATABASE_URL: str = "sqlite+aiosqlite:///./rag_agent.db"

    # LLM later on (position)
    OPENAI_API_KEY: str = ""
    OPENAI_API_BASE: str = "https://api.openai.com/v1"
    LLM_MODEL: str = "gpt-4o-mini"

    # embedding
    EMBEDDING_MODEL: str = "text-embedding-3-small"

    # vector store
    CHROMA_PATH: str = "./chroma_db"

    # chunking
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()