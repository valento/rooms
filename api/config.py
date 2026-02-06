import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # Database
    DB_USER = os.getenv("POSTGRES_USER", "admin")
    DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "changeme")
    DB_HOST = os.getenv("POSTGRES_HOST", "postgres")
    DB_PORT = os.getenv("POSTGRES_PORT", "5432")
    DB_NAME = os.getenv("POSTGRES_DB", "company_data")
    
    # Embedding model
    EMBEDDING_MODEL = "all-MiniLM-L6-v2"
    
    # API
    API_TITLE = "Company Search API"
    API_VERSION = "1.0.0"
    
    @property
    def database_url(self):
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

settings = Settings()