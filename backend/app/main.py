import asyncio
from contextlib import asynccontextmanager, suppress
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
from app.services.lama_inpaint import LamaUnavailableError, preload_lama_model
from app.services.redis_client import close_redis


settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    preload_task = None
    Base.metadata.create_all(bind=engine)
    run_compat_migrations(engine)
    db = SessionLocal()
    try:
        ensure_default_admin(db)
    finally:
        db.close()
    if settings.inpaint_lama_preload:
        async def warm_lama() -> None:
            try:
                await preload_lama_model(settings)
            except LamaUnavailableError:
                pass

        preload_task = asyncio.create_task(warm_lama())
    yield
    if preload_task is not None and not preload_task.done():
        preload_task.cancel()
        with suppress(asyncio.CancelledError):
            await preload_task
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
