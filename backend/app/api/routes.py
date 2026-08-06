from fastapi import APIRouter


router = APIRouter()


@router.get("/")
def root():

    return {
        "app": "SLATE Backend",
        "status": "running",
    }


@router.get("/health")
def health():

    return {
        "status": "healthy",
    }