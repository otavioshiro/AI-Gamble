from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Redis configuration
    REDIS_URL: str

    # OpenAI API configuration
    OPENAI_API_KEY: str
    OPENAI_BASE_URL: str
    OPENAI_MODEL: str
    NODE_NUM: int

    # Inactive game cleanup threshold (in hours)
    INACTIVE_GAME_CLEANUP_HOURS: int

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'

settings = Settings()