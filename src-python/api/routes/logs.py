from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse
from core.logger import broadcaster, log_generator

router = APIRouter(prefix="/logs", tags=["logs"])


@router.get("/history")
def get_history():
    return broadcaster.history


@router.get("/stream")
def stream_logs():
    return EventSourceResponse(log_generator())
