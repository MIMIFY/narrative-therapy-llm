from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openrouter_api_key: str
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    stage_planner_model: str = "openai/gpt-4o"
    reflection_planner_model: str = "openai/gpt-4o-mini"
    response_model: str = "openai/gpt-4o"
    goal_checker_model: str = "openai/gpt-4o-mini"
    embedding_model: str = "BAAI/bge-m3"
    chroma_persist_dir: str = "./chroma_db"
    database_path: str = "./sessions.db"

    class Config:
        env_file = ".env"


settings = Settings()
