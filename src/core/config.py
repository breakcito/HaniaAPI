import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    PROJECT_NAME: str = "Hania Facturador API"
    VERSION: str = "1.0.0"
    
    # Base de datos MySQL
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", "3306"))
    DB_DATABASE: str = os.getenv("DB_DATABASE", "")
    DB_USERNAME: str = os.getenv("DB_USERNAME", "")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
    
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        return f"mysql+pymysql://{self.DB_USERNAME}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_DATABASE}?charset=utf8mb4"

    # Seguridad JWT
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "43200"))

    # Conexión con Factos API
    API_FACTURADOR_URL: str = os.getenv("API_FACTURADOR_URL", "").rstrip("/")
    API_KEY_FACTURADOR: str = os.getenv("API_KEY_FACTURADOR", "")
    WEBHOOK_SECRET: str = os.getenv("WEBHOOK_SECRET", "")
    FACTOS_USER_EMAIL: str = os.getenv("FACTOS_USER_EMAIL", "")
    FACTOS_USER_PASSWORD: str = os.getenv("FACTOS_USER_PASSWORD", "")
    FACTOS_COMPANY_ID: str = os.getenv("FACTOS_COMPANY_ID", "")
    # URL pública de este API a la que Factos enviará los webhooks (ej. https://api.hania.pe/api/webhooks/factos)
    HANIA_WEBHOOK_URL: str = os.getenv("HANIA_WEBHOOK_URL", "")

    # Configuración inicial de empresa y usuario
    ADMIN_INITIAL_USERNAME: str = os.getenv("ADMIN_INITIAL_USERNAME", "admin")
    ADMIN_INITIAL_PASSWORD: str = os.getenv("ADMIN_INITIAL_PASSWORD", "")
    DEFAULT_COMPANY_RUC: str = os.getenv("DEFAULT_COMPANY_RUC", "")
    DEFAULT_COMPANY_NAME: str = os.getenv("DEFAULT_COMPANY_NAME", "")
    DEFAULT_BN_ACCOUNT: str = os.getenv("DEFAULT_BN_ACCOUNT", "")

settings = Settings()
