import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from .database import init_db
from .core.rag_engine import rag_engine
from .routers import chat, sessions


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database and RAG engine on startup
    await init_db()
    from .config import settings

    if settings.disable_rag:
        print("RAG 引擎已禁用：DISABLE_RAG=1，仅用于本地快速测试。")
    else:
        print("正在初始化 RAG 引擎（首次运行会下载 BGE-M3 模型，约 600MB）...")
        rag_engine.initialize()
        print("RAG 引擎初始化完成 ✓")
    yield


app = FastAPI(
    title="INT - Interactive Narrative Therapist",
    description="叙事疗法 AI 咨询师系统",
    version="1.0.0",
    lifespan=lifespan,
)

# Register API routers first (so /api/* routes take priority)
app.include_router(chat.router)
app.include_router(sessions.router)

# Health check endpoint
@app.get("/health")
async def health():
    return {"status": "ok", "service": "INT Narrative Therapist"}

# Serve frontend — html=True makes StaticFiles serve index.html at "/" and
# keeps relative paths (style.css, app.js) working without any changes to
# the HTML source.
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
