from fastapi import APIRouter
from core.config import settings_manager, Settings
from core.logger import setup_logging

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/")
def get_settings() -> Settings:
    return settings_manager.get()


@router.put("/")
def update_settings(payload: dict) -> Settings:
    new_settings = settings_manager.update(payload)
    setup_logging()  # Refresh logger config in case debug_logging changed
    return new_settings
