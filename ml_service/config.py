from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    app_name: str = "Videx ML Service"
    
                      
    data_dir: str = "data"
    index_dir: str = "data/indexes"
    
                     
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dim: int = 384                                  
    
                  
    llm_provider: str = "stub"                 
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    
                        
    default_top_k: int = 5
    
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}
    
    def ensure_directories(self):
        """Create data directories if they don't exist"""
        Path(self.data_dir).mkdir(parents=True, exist_ok=True)
        Path(self.index_dir).mkdir(parents=True, exist_ok=True)


settings = Settings()

