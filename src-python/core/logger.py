import logging
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

        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


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

        # Put to all listeners, but handle cases where queue is full
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

    # Remove all existing sinks
    logger.remove()

    # 1. Console Logger
    logger.add(
        sys.stderr,
        level=log_level,
        colorize=True,
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    )

    # 2. File Logger (Standard Text)
    logger.add(
        LOG_DIR / "sidecar.log",
        rotation="10 MB",
        level=log_level,
        retention="1 week",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
    )

    # 3. JSON Logger (For API/Broadcaster)
    logger.add(broadcaster.sink, level=log_level)

    # Intercept standard library logging
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

    # Optional: silence extremely noisy loggers
    for noisy in ["uvicorn.access", "httpx", "httpcore"]:
        logging.getLogger(noisy).setLevel(logging.WARNING)

    # Intercept all existing loggers
    for name in logging.root.manager.loggerDict.keys():
        _logger = logging.getLogger(name)
        _logger.handlers = [InterceptHandler()]
        _logger.propagate = False
