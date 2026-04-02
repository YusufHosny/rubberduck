import os
import socket
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging

from core.db import init_db, DATA_DIR
from core.config import settings_manager
from api.routes import projects, resources, chat, settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing database...")
    init_db()
    yield
    pass


app = FastAPI(title="Rubberduck Sidecar API", lifespan=lifespan)

# Allow CORS since it's a sidecar to the local frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(settings.router)
app.include_router(projects.router)
app.include_router(resources.router)
app.include_router(chat.router)


@app.get("/health")
def health_check():
    return {"status": "ok", "data_dir": str(DATA_DIR), "verify_rubberduck": True }


def is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


if __name__ == "__main__":
    app_settings = settings_manager.get()
    primary_port = app_settings.primary_port
    fallback_port = app_settings.fallback_port

    port_to_use = primary_port
    if is_port_in_use(primary_port):
        if is_port_in_use(fallback_port):
            print(
                f"Both primary ({primary_port}) and fallback ({fallback_port}) ports are in use. Exiting."
            )
            exit(1)
        port_to_use = fallback_port

    port = int(os.environ.get("RUBBERDUCK_PORT", port_to_use))
    logger.info(f"Starting server on port {port}")
    uvicorn.run("main:app", host="127.0.0.1", port=port, reload=False)
