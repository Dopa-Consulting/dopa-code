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
       D O P A   C O D E  -  Inti v{settings.version}
       Agente andino de orquestacion
    ============================================================
       DB: {settings.database_url}
       Dummy: {settings.dopa_code_dummy}
       Architect: {settings.architect_model}
       Executor:  {settings.executor_model}
       QA:        {settings.qa_model}
    ============================================================
       El Sol que ilumina tu codigo
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

    # Seed skills on startup
    from inti.skills_seeder import seed_all_skills
    skills_result = await seed_all_skills()
    print(f"  Skills: {skills_result['total']} loaded ({skills_result['new']} new, {skills_result['updated']} updated)")
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
            data = await websocket.receive_json()

            if data.get("type") == "chat" and data.get("stream"):
                from inti.gemini_interactions import gemini_interactions

                if gemini_interactions.is_configured:
                    async for chunk in gemini_interactions.interact_stream(
                        model=data.get("model", "gemini-2.5-flash"),
                        user_input=data.get("content", ""),
                        system_instruction=data.get("system"),
                    ):
                        await websocket.send_json(chunk)
                else:
                    await websocket.send_json({
                        "event_type": "error",
                        "payload": {"error": "DOPA_GOOGLE_API_KEY no configurada"}
                    })
            else:
                await websocket.send_json({
                    "event_type": "Echo",
                    "job_id": "",
                    "version": 1,
                    "payload": {"received": str(data)[:200]},
                })
    except WebSocketDisconnect:
        pass


# Serve PWA static files in production
frontend_dist = Path(__file__).parent.parent / "frontend-pwa" / "dist"
if getattr(sys, "frozen", False):
    frontend_dist = Path(sys._MEIPASS) / "frontend"

if frontend_dist.exists() and (frontend_dist / "index.html").exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")
