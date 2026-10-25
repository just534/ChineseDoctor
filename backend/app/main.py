import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from .config import get_settings
from .db import SessionLocal, engine
from .routers import ai, auth, cases, documents, misc, roles, users
from .services.bootstrap import bootstrap
from .services.importer import import_all

settings = get_settings()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("app")


def init_data() -> None:
    with SessionLocal() as db:
        bootstrap(db)
        import_all(db, settings.content_dir)


@asynccontextmanager
async def lifespan(_: FastAPI):
    # 开发环境启动即初始化；容器中由 entrypoint 的 `python -m app.cli init` 负责，避免多 worker 竞争
    if settings.auto_import:
        init_data()
    yield


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None if settings.is_production else "/api/docs",
    redoc_url=None,
    openapi_url=None if settings.is_production else "/api/openapi.json",
)

if settings.cors_origin_list:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.exception_handler(RequestValidationError)
async def validation_handler(_: Request, exc: RequestValidationError):
    errs = exc.errors()
    first = errs[0] if errs else {}
    field = ".".join(str(x) for x in first.get("loc", [])[1:])
    return JSONResponse(
        status_code=422,
        content={
            "detail": f"参数错误：{field} {first.get('msg', '')}".strip(),
            "errors": [{"loc": e.get("loc"), "msg": e.get("msg")} for e in errs],
        },
    )


@app.exception_handler(Exception)
async def unhandled(_: Request, exc: Exception):
    log.exception("未处理异常", exc_info=exc)
    return JSONResponse(status_code=500, content={"detail": "服务器内部错误"})


@app.middleware("http")
async def security_headers(request: Request, call_next):
    resp = await call_next(request)
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("X-Frame-Options", "DENY")
    resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    return resp


@app.get("/api/health", tags=["系统"])
def health():
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"status": "ok"}


for r in (auth.router, users.router, roles.router, documents.router, cases.router, misc.router, ai.router):
    app.include_router(r, prefix="/api")
