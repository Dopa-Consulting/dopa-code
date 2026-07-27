from fastapi import APIRouter

from inti.api import health, jobs, devices, audit, events, memory
from inti.api import tenants, templates, payments, openrouter, webauthn, voice, sessions, agent_comm, gemini_interactions, workspace

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
api_router.include_router(devices.router, prefix="/devices", tags=["devices"])
api_router.include_router(audit.router, prefix="/audit", tags=["audit"])
api_router.include_router(events.router, prefix="/events", tags=["events"])
api_router.include_router(memory.router, prefix="/memory", tags=["memory"])
api_router.include_router(tenants.router, prefix="/tenants", tags=["tenants"])
api_router.include_router(templates.router, prefix="/templates", tags=["templates"])
api_router.include_router(payments.router, prefix="/payments", tags=["payments"])
api_router.include_router(openrouter.router, prefix="/openrouter", tags=["openrouter"])
api_router.include_router(webauthn.router, prefix="/webauthn", tags=["webauthn"])
api_router.include_router(voice.router, prefix="/voice", tags=["voice"])
api_router.include_router(sessions.router, prefix="/sessions", tags=["sessions"])
api_router.include_router(agent_comm.router, prefix="/agent-comm", tags=["agent-comm"])
api_router.include_router(gemini_interactions.router, prefix="/gemini", tags=["gemini"])
api_router.include_router(workspace.router, prefix="/workspace", tags=["workspace"])
