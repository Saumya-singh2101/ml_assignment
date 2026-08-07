from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.services.analytics import init_db
from app.api.analyze import router as analyze_router
from app.api.analytics import router as analytics_router


app = FastAPI(
    title="SLATE Backend",
    description="AI Canvas backend for SLATE",
    version="1.0.0",
)


# --------------------------------------------------
# CORS
# --------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------
# DATABASE INITIALIZATION
# --------------------------------------------------

@app.on_event("startup")
def startup():
    init_db()


# --------------------------------------------------
# ROUTES
# --------------------------------------------------

app.include_router(
    analyze_router
)

app.include_router(
    analytics_router
)