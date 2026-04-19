from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "CWIE System"
    API_PREFIX: str = "/api/v1"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/cwie_db"

    # JWT
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_DAYS: int = 1

    # LINE Login
    LINE_CHANNEL_ID: str = ""
    LINE_CHANNEL_SECRET: str = ""
    LINE_CALLBACK_URL: str = "http://localhost:8000/api/v1/auth/line/callback"
    LINE_AUTH_URL: str = "https://access.line.me/oauth2/v2.1/authorize"
    LINE_TOKEN_URL: str = "https://api.line.me/oauth2/v2.1/token"
    LINE_PROFILE_URL: str = "https://api.line.me/v2/profile"

    # Frontend
    FRONTEND_URL: str = "http://localhost:5173"

    class Config:
        env_file = ".env"
        extra = "allow"


settings = Settings()
