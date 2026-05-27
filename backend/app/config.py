from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- OpenAI ---
    openai_api_key: str = ""
    openai_embedding_model: str = "text-embedding-3-small"
    openai_chat_model: str = "gpt-4o-mini"

    # --- Pinecone (vector / semantic search) ---
    pinecone_api_key: str = ""
    pinecone_index_name: str = "rag-hybrid"

    # --- Elasticsearch (keyword / BM25 search) ---
    es_host: str = "http://localhost:9200"
    es_index: str = "documents"

    # --- Redis (query result cache) ---
    redis_url: str = "redis://localhost:6379/0"
    redis_ttl: int = 3600  # seconds — how long to keep cached answers

    # --- Cohere re-ranker (optional — re-ranking is skipped if this is empty) ---
    cohere_api_key: str = ""

    # --- App ---
    app_port: int = 8000
    log_level: str = "INFO"

    # Load from .env file automatically; ignore extra vars
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


# Single shared instance — import this everywhere
settings = Settings()
