from fastapi import APIRouter

from inti.api import health, jobs, devices, audit, events, memory
from inti.api import tenants, templates, payments

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router, tags=["health"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
api_router.include_router(devices.router, prefix="/devices", tags=["devices"])
api_router.include_router(audit.router, prefix="/audit", tags=["audit"])
api_router.include_router(events.router, prefix="/events", tags=["events"])
api_router.include_router(memory.router, prefix="/memory", tags=["memory"])
api_router.include_router(tenants.router, prefix="/tenants", tags=["tenants"])
api_router.include_router(templates.router, prefix="/templates", tags=["templates"])
api_router.include_router(payments.router, prefix="/payments", tags=["payments"])
