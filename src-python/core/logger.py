import logging
from typing import Any, Dict, List, Optional, Union
from uuid import UUID
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult
from langchain_core.messages import BaseMessage
import sys
import json
import queue
import asyncio
from pathlib import Path
from loguru import logger
from core.config import settings_manager

DATA_DIR = Path.home() / "rubberduck"
LOG_DIR = DATA_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)


class InterceptHandler(logging.Handler):
    def emit(self, record):
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = logging.currentframe(), 0
        while frame and (depth == 0 or frame.f_code.co_filename == logging.__file__):
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


class LoguruCallbackHandler(BaseCallbackHandler):
    def on_llm_start(
        self,
        serialized: Dict[str, Any],
        prompts: List[str],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Any:
        logger.debug(f"LLM Started (run_id={run_id}): {prompts}")

    def on_chat_model_start(
        self,
        serialized: Dict[str, Any],
        messages: List[List[BaseMessage]],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Any:
        try:
            msgs_repr = "\n".join(
                [str([m.content for m in msg_list]) for msg_list in messages]
            )
            logger.debug(f"Chat Model Started (run_id={run_id}):\n{msgs_repr}")
        except Exception:
            logger.debug(f"Chat Model Started (run_id={run_id}): {messages}")

    def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        logger.debug(f"LLM Ended (run_id={run_id}): {response.generations}")

    def on_llm_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        logger.error(f"LLM Error (run_id={run_id}): {error}")

    def on_tool_start(
        self,
        serialized: Dict[str, Any],
        input_str: str,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        inputs: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Any:
        tool_name = (
            serialized.get("name", "Unknown Tool") if serialized else "Unknown Tool"
        )
        logger.debug(f"Tool Started ({tool_name}): {inputs or input_str}")

    def on_tool_end(
        self,
        output: Any,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        logger.debug(f"Tool Ended: {output}")

    def on_tool_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        logger.error(f"Tool Error: {error}")


class LogBroadcaster:
    def __init__(self):
        self.listeners = set()
        self.history = []

    def sink(self, message):
        record = message.record
        log_data = {
            "time": record["time"].isoformat(),
            "level": record["level"].name,
            "message": record["message"],
            "name": record["name"],
            "file": record["file"].name,
            "line": record["line"],
        }
        self.history.append(log_data)
        if len(self.history) > 500:
            self.history.pop(0)

        log_str = json.dumps(log_data)

        dead_listeners = []
        for q in list(self.listeners):
            try:
                q.put_nowait(log_str)
            except queue.Full:
                pass
            except Exception:
                dead_listeners.append(q)

        for q in dead_listeners:
            self.listeners.discard(q)


broadcaster = LogBroadcaster()


async def log_generator():
    q = queue.Queue(maxsize=200)
    broadcaster.listeners.add(q)
    try:
        while True:
            try:
                msg = q.get_nowait()
                yield {"data": msg}
            except queue.Empty:
                await asyncio.sleep(0.1)
    finally:
        broadcaster.listeners.discard(q)


def setup_logging():
    settings = settings_manager.get()
    log_level = "DEBUG" if settings.debug_logging else "INFO"

    logger.remove()

    logger.add(
        sys.stderr,
        level=log_level,
        colorize=True,
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    )

    logger.add(
        LOG_DIR / "sidecar.log",
        rotation="10 MB",
        level=log_level,
        retention="1 week",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
    )

    logger.add(broadcaster.sink, level=log_level)

    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

    noisy_level = logging.INFO if log_level == "DEBUG" else logging.WARNING
    for noisy in [
        "uvicorn.access",
        "httpx",
        "httpcore",
        "sse_starlette",
        "sse_starlette.sse",
    ]:
        logging.getLogger(noisy).setLevel(noisy_level)

    for name in logging.root.manager.loggerDict.keys():
        _logger = logging.getLogger(name)
        _logger.handlers = [InterceptHandler()]
        _logger.propagate = False
