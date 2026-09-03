from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.database import engine, Base
from core.config import settings
from api.v1 import auth, organizations, incidents, responders, assignments, admin

Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.APP_NAME, version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(organizations.router, prefix="/api/v1")
app.include_router(incidents.router, prefix="/api/v1")
app.include_router(responders.router, prefix="/api/v1")
app.include_router(assignments.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/ready")
def ready():
    return {"status": "ready"}
