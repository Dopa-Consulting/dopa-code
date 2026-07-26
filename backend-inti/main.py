import json
import sys
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

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

            if data.get("type") == "chat":
                content = data.get("content", "")
                use_stream = data.get("stream", False)

                # Try Gemini Interactions API first
                from inti.gemini_interactions import gemini_interactions

                if gemini_interactions.is_configured and use_stream:
                    async for chunk in gemini_interactions.interact_stream(
                        model=data.get("model", "gemini-2.5-flash"),
                        user_input=content,
                    ):
                        await websocket.send_json(chunk)
                elif gemini_interactions.is_configured:
                    result = await gemini_interactions.interact(
                        model=data.get("model", "gemini-2.5-flash"),
                        user_input=content,
                        system_instruction="Eres Inti, el agente andino de Dopa Code. Dopa Code es un entorno de desarrollo agentico Local-First que orquesta la escritura, revision y despliegue de codigo desde una PC, controlado desde una PWA movil. NO es sobre dopamina ni neurociencia. Responde en español.",
                    )
                    if "error" not in result:
                        await websocket.send_json({
                            "event_type": "chat_response",
                            "payload": {"content": result.get("output", ""), "model": result.get("model", "gemini"), "usage": result.get("usage", {})}
                        })
                    else:
                        # Gemini fallo, cae a OpenRouter
                        from inti.openrouter_client import openrouter
                        if openrouter.is_configured:
                            or_result = await openrouter.chat(
                                model="deepseek/deepseek-chat",
                                messages=[{"role": "user", "content": content}],
                                max_tokens=1000,
                            )
                            await websocket.send_json({
                                "event_type": "chat_response",
                                "payload": {
                                    "content": or_result.get("content", or_result.get("error", "Error")),
                                    "model": "openrouter (gemini fallback)",
                                    "usage": or_result.get("usage", {}),
                                }
                            })
                        else:
                            await websocket.send_json({
                                "event_type": "error",
                                "payload": {"error": result.get("error", "Unknown error")}
                            })
                else:
                    # Fallback to OpenRouter
                    from inti.openrouter_client import openrouter
                    if openrouter.is_configured:
                        result = await openrouter.chat(
                            model="deepseek/deepseek-chat",
                            messages=[{"role": "user", "content": content}],
                            max_tokens=1000,
                        )
                        await websocket.send_json({
                            "event_type": "chat_response",
                            "payload": {
                                "content": result.get("content", result.get("error", "Error")),
                                "model": result.get("model", "openrouter"),
                                "usage": result.get("usage", {}),
                            }
                        })
                    else:
                        await websocket.send_json({
                            "event_type": "error",
                            "payload": {"error": "No LLM configured. Configura OpenRouter o Gemini en Modelos."}
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
    from fastapi.responses import FileResponse

    # Catch-all: serve index.html for SPA client-side routing
    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str):
        file_path = frontend_dist / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(frontend_dist / "index.html")
