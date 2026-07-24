from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def health():
    return {"status": "healthy", "daemon": "Inti"}


@router.get("/ready")
async def ready():
    return {"status": "ready"}
