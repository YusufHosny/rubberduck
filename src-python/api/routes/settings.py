from fastapi import APIRouter
from core.config import settings_manager, Settings

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/")
def get_settings() -> Settings:
    return settings_manager.get()


@router.put("/")
def update_settings(payload: dict) -> Settings:
    return settings_manager.update(payload)
