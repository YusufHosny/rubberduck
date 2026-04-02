import json
from pathlib import Path
from pydantic import BaseModel

DATA_DIR = Path.home() / "rubberduck"
SETTINGS_PATH = DATA_DIR / "settings.json"


class Settings(BaseModel):
    theme: str = "system"
    provider: str = "vertexai"
    model: str = "gemini-3-flash"
    embedding_provider: str = "vertexai"
    embedding_model: str = "text-embedding-004"
    rag_threshold: int = 100000
    chunk_size: int = 1000
    chunk_overlap: int = 200
    openai_key: str = ""
    vertex_project: str = ""
    vertex_location: str = "global"
    ollama_url: str = "http://localhost:11434"
    primary_port: int = 38438
    fallback_port: int = 38439


class SettingsManager:
    def __init__(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.settings = self._load()

    def _load(self) -> Settings:
        if SETTINGS_PATH.exists():
            try:
                with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return Settings(**data)
            except Exception as e:
                print(f"Error loading settings: {e}")

        default_settings = Settings()
        self._save(default_settings)
        return default_settings

    def _save(self, settings: Settings):
        with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
            f.write(settings.model_dump_json(indent=4))

    def get(self) -> Settings:
        # Always read fresh in case it was modified externally or by frontend
        return self._load()

    def update(self, new_settings: dict) -> Settings:
        current = self._load()
        updated_data = current.model_dump()
        updated_data.update(new_settings)
        updated_settings = Settings(**updated_data)
        self._save(updated_settings)
        self.settings = updated_settings
        return self.settings


settings_manager = SettingsManager()
