import json
import sys
import subprocess
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from inti.config import settings
from inti.database import engine, Base
from inti.models import (  # noqa: F401 - register all models for table creation
    Job, JobStep, Diff, Approval, AuditLog, Event, CiRun, Device,
    ExperienceLesson, SkillDefinition, SkillExecution, ProjectKnowledge,
    Tenant, PaymentIntegration,
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
    from inti.openrouter_client import openrouter, multiprovider
    or_loaded = await openrouter.load_key()
    mp_loaded = await multiprovider.load_keys()
    print(f"  OpenRouter: {'configured' if or_loaded else 'not set'} | Direct providers: {mp_loaded} loaded")
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

# Auth middleware
PUBLIC_PATHS = ["/health", "/login", "/favicon.svg", "/manifest.json", "/sw.js", "/assets"]

@app.middleware("http")
async def auth_middleware(request, call_next):
    path = request.url.path
    if any(path.startswith(p) for p in PUBLIC_PATHS):
        return await call_next(request)
    token = request.cookies.get("dopa_token") or request.headers.get("x-dopa-token") or request.query_params.get("token")
    if token == settings.access_token:
        return await call_next(request)
    if path == "/" or path == "/login":
        return await call_next(request)
    return JSONResponse({"error": "Unauthorized"}, status_code=401)


from inti.router import api_router
app.include_router(api_router)


@app.get("/health")
async def health_check():
    return {"status": "ok", "daemon": "Inti", "version": settings.version, "dummy_mode": settings.dopa_code_dummy}


@app.get("/login")
async def login(token: str = ""):
    if token == settings.access_token:
        resp = JSONResponse({"status": "ok"})
        resp.set_cookie("dopa_token", token, httponly=False, max_age=86400 * 30)
        return resp
    return JSONResponse({"error": "Invalid token"}, status_code=401)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    await websocket.send_json({"event_type": "ConnectionEstablished", "job_id": "", "version": 1, "payload": {"message": "Conectado a Inti"}})

    try:
        while True:
            data = await websocket.receive_json()
            if data.get("type") != "chat":
                await websocket.send_json({"event_type": "Echo", "payload": {"received": str(data)[:200]}})
                continue

            content = data.get("content", "")
            workspace = str(Path.cwd())

            from inti.agent_loop import AgentLoop

            loop = AgentLoop(workspace=workspace, profile=data.get("profile"))
            await loop.run(content, emit=websocket.send_json)

    except WebSocketDisconnect:
        pass


# SPA fallback
frontend_dist = Path(__file__).parent.parent / "frontend-pwa" / "dist"
if getattr(sys, "frozen", False):
    frontend_dist = Path(sys._MEIPASS) / "frontend"

if frontend_dist.exists() and (frontend_dist / "index.html").exists():
    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str):
        file_path = frontend_dist / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(frontend_dist / "index.html")
