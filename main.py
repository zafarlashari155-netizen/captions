from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import captions, auth_router, billing
from app.config import settings
from app.database import engine, Base
from app.models import db_models  # noqa
from app.services.cleanup import cleanup_old_jobs

Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    cleanup_old_jobs()
    yield

app = FastAPI(title="Harf Captions API", lifespan=lifespan)
app.add_middleware(CORSMiddleware,
    allow_origins=[o.strip() for o in settings.allowed_origin.split(",") if o.strip()],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
app.include_router(captions.router)
app.include_router(auth_router.router)
app.include_router(billing.router)

@app.get("/health")
def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=settings.port, reload=True)
