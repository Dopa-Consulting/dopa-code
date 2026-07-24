import json
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

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
