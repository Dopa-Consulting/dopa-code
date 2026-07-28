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

# Auth middleware: protege solo si hay token configurado
# Si no hay token, todo es publico (dev mode). Si hay, requiere auth.
SKIP_AUTH = not settings.access_token or settings.access_token == "cambiar-en-produccion"

PUBLIC_PATHS = ["/health", "/login", "/favicon.svg", "/manifest.json", "/sw.js", "/assets", "/api"]

@app.middleware("http")
async def auth_middleware(request, call_next):
    if SKIP_AUTH:
        return await call_next(request)
    path = request.url.path
    if any(path.startswith(p) for p in PUBLIC_PATHS + ["/"]):
        return await call_next(request)
    token = request.cookies.get("dopa_token")
    if token == settings.access_token:
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

    # Historial de conversación POR CONEXIÓN (Bug 1: cada mensaje era una sesión
    # nueva; AgentLoop.run acepta `history` pero main.py nunca lo pasaba, así que
    # Inti no recordaba nada dentro de una misma conversación).
    history: list[dict] = []
    session_id: str = ""
    try:
        while True:
            data = await websocket.receive_json()
            if data.get("type") != "chat":
                await websocket.send_json({"event_type": "Echo", "payload": {"received": str(data)[:200]}})
                continue

            content = data.get("content", "")
            ws_in = data.get("workspace", "")
            workspace = ws_in if ws_in and Path(ws_in).is_dir() else str(Path.cwd())

            # Resetear sesion si el frontend pide nuevo chat
            if data.get("new_session"):
                session_id = ""
                history = []
                await websocket.send_json({
                    "event_type": "session_reset",
                    "payload": {"message": "Nueva sesion iniciada"}
                })
                continue

            # Auto-crear sesion por conexion (no global)
            if not session_id:
                from inti.orchestrator import orchestrator
                role = "builder" if content and content.lower().split()[0] in ["crea","genera","construye","hace","diseña"] else "architect"
                s = orchestrator.create_session(role=role, workspace_path=workspace)
                session_id = s.id
                await websocket.send_json({
                    "event_type": "session_created",
                    "payload": {"session_id": session_id, "workspace": workspace}
                })

            from inti.agent_loop import AgentLoop

            # Combinar historial del frontend (sobrevive reconexiones) con el del server
            client_history = data.get("history", [])
            merged_history = client_history if client_history else history

            final_reply: dict = {"content": ""}
            session_titled = False

            async def emit(ev):
                nonlocal session_titled
                if ev.get("event_type") == "chat_response":
                    final_reply["content"] = ev.get("payload", {}).get("content", "")
                    # Poner titulo a la sesion con la primera respuesta del agente (max 60 chars)
                    if not session_titled and final_reply["content"] and session_id:
                        title = final_reply["content"].split("\n")[0].strip().strip("*").strip("#")[:60]
                        if title and len(title) > 3:
                            from inti.orchestrator import orchestrator
                            s = orchestrator.get_session(session_id)
                            if s and not s.metadata.get("title"):
                                s.metadata["title"] = title
                                session_titled = True
                await websocket.send_json(ev)

            loop = AgentLoop(
                workspace=workspace,
                profile=data.get("profile"),
                require_approval=data.get("require_approval", data.get("profile") is not None),
                allowed_dirs=data.get("allowed_dirs"),
            )
            await loop.run(content, emit=emit, history=merged_history)

            history.append({"role": "user", "content": content})
            if final_reply["content"]:
                history.append({"role": "assistant", "content": final_reply["content"]})
            if len(history) > 20:
                del history[: len(history) - 20]

            # Persistir mensajes en DB
            if session_id:
                try:
                    from inti.database import async_session as a_s
                    from inti.models.conversation_message import ConversationMessage
                    async with a_s() as db:
                        db.add(ConversationMessage(session_id=session_id, role="user", content=content))
                        if final_reply["content"]:
                            db.add(ConversationMessage(session_id=session_id, role="assistant", content=final_reply["content"]))
                        await db.commit()
                except Exception:
                    pass

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
