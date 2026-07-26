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
            use_stream = data.get("stream", False)
            workspace = str(Path.cwd())

            # 1. Ejecutar comando real
            from inti.chat_commands import execute_chat_command
            cmd_result = await execute_chat_command(workspace, content)

            if cmd_result["type"] == "action":
                await websocket.send_json({"event_type": "chat_response", "payload": {"content": cmd_result["content"], "model": "inti-action"}})

                # Si creo un job → stream OpenCode via bridge
                is_job = "job" in cmd_result.get("content", "").lower()
                if is_job:
                    await websocket.send_json({"event_type": "step.start", "data": {"type": "opencode"}})
                    try:
                        import httpx as _httpx
                        async with _httpx.AsyncClient(timeout=120.0) as client:
                            async with client.stream(
                                "POST", "http://localhost:4097/run-stream",
                                headers={"x-bridge-token": "dopa-bridge-local-dev"},
                                json={"prompt": content, "directory": workspace, "agent": "build"},
                            ) as resp:
                                async for line in resp.aiter_lines():
                                    if line.startswith("data: "):
                                        try:
                                            chunk = json.loads(line[6:])
                                            await websocket.send_json({"event_type": "step.delta", "data": chunk})
                                        except Exception:
                                            pass
                    except Exception:
                        pass
                    # Git diff
                    try:
                        r = subprocess.run(["git", "diff", "--stat"], cwd=workspace, capture_output=True, text=True, timeout=10)
                        if r.stdout.strip():
                            await websocket.send_json({"event_type": "chat_response", "payload": {"content": "**Git diff**:\n```\n" + r.stdout.strip()[:2000] + "\n```", "model": "git"}})
                    except Exception:
                        pass
                    await websocket.send_json({"event_type": "step.stop", "data": {"index": 0}})

            else:
                # 2. Conversacion → LLM
                from inti.gemini_interactions import gemini_interactions
                from inti.openrouter_client import openrouter as or_client

                if gemini_interactions.is_configured:
                    identity = "Eres Inti, agente andino de Dopa Code. Responde en español, en primera persona.\n\n"
                    result = await gemini_interactions.interact(model="gemini-2.5-flash", user_input=identity + content)
                    if "error" not in result:
                        await websocket.send_json({"event_type": "chat_response", "payload": {"content": result.get("output", ""), "model": "gemini", "usage": result.get("usage", {})}})
                    elif or_client.is_configured:
                        r = await or_client.chat(model="deepseek/deepseek-chat", messages=[{"role": "user", "content": content}], max_tokens=1000)
                        await websocket.send_json({"event_type": "chat_response", "payload": {"content": r.get("content", "Error"), "model": "openrouter", "usage": r.get("usage", {})}})
                    else:
                        await websocket.send_json({"event_type": "error", "payload": {"error": result.get("error", "Unknown")}})
                elif or_client.is_configured:
                    r = await or_client.chat(model="deepseek/deepseek-chat", messages=[{"role": "user", "content": content}], max_tokens=1000)
                    await websocket.send_json({"event_type": "chat_response", "payload": {"content": r.get("content", "Error"), "model": "openrouter", "usage": r.get("usage", {})}})
                else:
                    await websocket.send_json({"event_type": "error", "payload": {"error": "No LLM configured"}})

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
