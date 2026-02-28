from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str # Added SECRET_KEY
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # Default to 7 days
    
    BLOCKCHAIN_ENABLED: bool = False
    BLOCKCHAIN_ORACLE_URL: str = ""
    BLOCKCHAIN_REQUEST_TIMEOUT_SECONDS: int = 20
    BLOCKCHAIN_DISPATCH_DEADLINE_HOURS: int = 24
    
    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()
