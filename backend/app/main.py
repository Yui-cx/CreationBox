from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from app.api import admin, auth, generations, images, users
from app.core.config import get_settings
from app.db.compat import run_compat_migrations
from app.db.session import Base, SessionLocal, engine
from app.models import entities  # noqa: F401
from app.services.default_user import ensure_default_admin
from app.services.redis_client import close_redis


settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    run_compat_migrations(engine)
    db = SessionLocal()
    try:
        ensure_default_admin(db)
    finally:
        db.close()
    yield
    await close_redis()


app = FastAPI(title="CreationBox API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(ValidationError)
async def validation_exception_handler(_: Request, exc: ValidationError):
    return JSONResponse(status_code=422, content={"detail": "VALIDATION_ERROR", "errors": exc.errors()})


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(users.router, prefix=settings.api_prefix)
app.include_router(generations.router, prefix=settings.api_prefix)
app.include_router(images.router, prefix=settings.api_prefix)
app.include_router(admin.router, prefix=settings.api_prefix)
