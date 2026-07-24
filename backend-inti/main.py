import json
import sys
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from inti.config import settings
from inti.database import engine, Base
from inti.models import (  # noqa: F401 - register all models for table creation
    Job,
    JobStep,
    Diff,
    Approval,
    AuditLog,
    Event,
    CiRun,
    Device,
    ExperienceLesson,
    SkillDefinition,
    SkillExecution,
    ProjectKnowledge,
    Tenant,
    PaymentIntegration,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    banner = f"""
    ============================================================
       Dopa Code - Inti (v{settings.version})
       Agente andino de orquestacion
    ============================================================
       DB: {settings.database_url}
       Dummy Mode: {settings.dopa_code_dummy}
       Architect: {settings.architect_model}
       Executor:  {settings.executor_model}
       QA:        {settings.qa_model}
       Tables:    {len(Base.metadata.tables)}
    ============================================================
    """
    print(banner)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Load persisted provider keys on startup
    from inti.openrouter_client import openrouter, multiprovider
    or_loaded = await openrouter.load_key()
    mp_loaded = await multiprovider.load_keys()
    provider_status = "configured" if or_loaded else "not set"
    print(f"  OpenRouter: {provider_status} | Direct providers: {mp_loaded} loaded")
    yield
    await engine.dispose()


app = FastAPI(
    title="Dopa Code - Inti",
    description="Agente andino de orquestacion para Dopa Code",
    version=settings.version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from inti.router import api_router

app.include_router(api_router)


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "daemon": "Inti",
        "version": settings.version,
        "dummy_mode": settings.dopa_code_dummy,
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    await websocket.send_json({
        "event_type": "ConnectionEstablished",
        "job_id": "",
        "version": 1,
        "payload": {"message": "Conectado a Inti"},
    })
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_json({
                "event_type": "Echo",
                "job_id": "",
                "version": 1,
                "payload": {"received": data},
            })
    except WebSocketDisconnect:
        pass


# Serve PWA static files in production
frontend_dist = Path(__file__).parent.parent / "frontend-pwa" / "dist"
if getattr(sys, "frozen", False):
    frontend_dist = Path(sys._MEIPASS) / "frontend"

if frontend_dist.exists() and (frontend_dist / "index.html").exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")
