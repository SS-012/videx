from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    app_name: str = "Videx"
    allow_origin: str = "http://localhost:3000"

                          
    data_dir: str = "data"
    documents_dir: str = "data/documents"
    annotations_dir: str = "data/annotations"

                   
    provider_mode: str = "stub"                          
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    ollama_base_url: str | None = None
    ollama_model: str = "llama3.1"
    request_timeout_s: int = 60

                                 
    ml_service_url: str = "http://localhost:8001"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}
    
    def ensure_directories(self):
        """Create data directories if they don't exist"""
        Path(self.data_dir).mkdir(parents=True, exist_ok=True)
        Path(self.documents_dir).mkdir(parents=True, exist_ok=True)
        Path(self.annotations_dir).mkdir(parents=True, exist_ok=True)


settings = Settings()
