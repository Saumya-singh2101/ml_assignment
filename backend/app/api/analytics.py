
from fastapi import APIRouter, HTTPException

from app.services.analytics import (
    get_analytics,
    update_outcome,
)


router = APIRouter()


# ============================================================
# ANALYTICS SUMMARY
# ============================================================

@router.get("/api/analytics")
def analytics():
    return get_analytics()


# ============================================================
# ACCEPT ANALYSIS
# ============================================================

@router.post(
    "/api/analyze/{request_id}/accept"
)
def accept_analysis(request_id: str):

    try:

        update_outcome(
            request_id=request_id,
            outcome="accepted",
        )

        return {
            "request_id": request_id,
            "outcome": "accepted",
            "message": "Analysis accepted successfully.",
        }

    except Exception as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )


# ============================================================
# DISCARD ANALYSIS
# ============================================================

@router.post(
    "/api/analyze/{request_id}/discard"
)
def discard_analysis(request_id: str):

    try:

        update_outcome(
            request_id=request_id,
            outcome="discarded",
        )

        return {
            "request_id": request_id,
            "outcome": "discarded",
            "message": "Analysis discarded successfully.",
        }

    except Exception as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )
