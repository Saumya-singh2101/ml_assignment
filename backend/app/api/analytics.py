from fastapi import APIRouter

from app.services.analytics import get_analytics


router = APIRouter()


@router.get("/api/analytics")
def analytics():
    return get_analytics()