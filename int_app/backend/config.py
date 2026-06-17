from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openrouter_api_key: str
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    stage_planner_model: str = "google/gemini-2.5-flash"
    reflection_planner_model: str = "google/gemini-2.5-flash"
    response_model: str = "google/gemini-2.5-flash"
    goal_checker_model: str = "google/gemini-2.5-flash"
    embedding_model: str = "BAAI/bge-m3"
    chroma_persist_dir: str = "./chroma_db"
    database_path: str = "./sessions.db"
    admin_key: str = "INT-research-2025"

    class Config:
        env_file = ".env"


settings = Settings()
