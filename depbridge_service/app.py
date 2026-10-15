from contextlib import asynccontextmanager
import logging
import os

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException

from .capsule import build_capsule
from .config import Settings
from .models import CreateAnalysis, CreateVerification
from .service import Service, ServiceError, redact
from .ui import ASSETS, primary_frontend, render_primary


def create_app(settings=None, engine=None):
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app):
        app.state.service = Service(settings, engine)
        yield
        app.state.service.close()

    app = FastAPI(title="DepBridge", version="1.0", lifespan=lifespan)

    @app.middleware("http")
    async def headers(request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(ServiceError)
    async def service_error(request, exc):
        headers = {"Retry-After": "5"} if exc.status == 429 else None
        return JSONResponse({"error": redact(exc.error)}, status_code=exc.status, headers=headers)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        # Do not reflect submitted bodies or secrets in error responses.
        fields = [".".join(str(part) for part in error["loc"]) for error in exc.errors()]
        return JSONResponse({"error": dict(code="validation_error", message="Invalid request fields: " + ", ".join(fields), retryable=False)}, status_code=422)

    @app.exception_handler(HTTPException)
    async def http_error(request, exc):
        return JSONResponse({"error": dict(code="not_found" if exc.status_code == 404 else "http_error", message=str(exc.detail), retryable=False)}, status_code=exc.status_code)

    @app.exception_handler(Exception)
    async def unexpected_error(request, exc):
        logging.getLogger("depbridge").error("Service request failed (%s)", type(exc).__name__)
        return JSONResponse({"error": dict(code="service_error", message="The service could not complete this request.", retryable=True)}, status_code=500)

    @app.get("/api/health")
    def health(request: Request):
        return dict(status="ready", schema_version="1.0", worker_count=1,
                    engine_available=request.app.state.service.engine.available(),
                    engine_mode=settings.engine_mode,
                    model_configured=bool(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")),
                    frontend_available=(settings.frontend_dir / "index.html").is_file())

    @app.post("/api/analyses", status_code=202)
    def create_analysis(body: CreateAnalysis, request: Request):
        return request.app.state.service.create(body)

    @app.get("/api/analyses/{analysis_id}")
    def get_analysis(analysis_id: str, request: Request):
        service = request.app.state.service
        return service.public(service.get(analysis_id))

    @app.post("/api/analyses/{analysis_id}/verifications", status_code=202)
    def verification(analysis_id: str, body: CreateVerification, request: Request):
        return request.app.state.service.verify(analysis_id, body)

    @app.get("/api/analyses/{analysis_id}/capsule.zip")
    def capsule(analysis_id: str, request: Request):
        content = build_capsule(request.app.state.service, analysis_id)
        return Response(content, media_type="application/zip", headers={"Content-Disposition": f'attachment; filename="{analysis_id}-capsule.zip"'})

    @app.get("/api/analyses/{analysis_id}/patches/{verification_id}.diff")
    def patch(analysis_id: str, verification_id: str, request: Request):
        service = request.app.state.service
        with service.store.lock:
            record = service.get(analysis_id)
            stored = record["_patches"].get(verification_id)
            if not stored:
                raise ServiceError(404, "patch_unavailable", "No patch was produced for this verification.")
            path = (settings.data_dir / stored).resolve()
            if not path.is_relative_to(settings.data_dir) or not path.is_file() or path.is_symlink():
                raise ServiceError(404, "patch_unavailable", "The recorded patch file is unavailable.")
            return Response(redact(path.read_text(encoding="utf-8")), media_type="text/x-diff",
                            headers={"Content-Disposition": f'attachment; filename="{verification_id}.diff"'})

    @app.get("/reports/{analysis_id}")
    def report(analysis_id: str, request: Request):
        request.app.state.service.get(analysis_id)
        index = settings.frontend_dir / "index.html"
        if not index.is_file():
            return HTMLResponse("<!doctype html><html lang='en'><title>DepBridge</title><h1>DepBridge</h1>"
                "<p>Report frontend not implemented in this checkout. The API is available at /api and /docs.</p></html>", status_code=503)
        if primary_frontend(settings.frontend_dir):
            return HTMLResponse(render_primary(index), headers={"Cache-Control": "no-cache"})
        return FileResponse(index, media_type="text/html", headers={"Cache-Control": "no-cache"})

    @app.get("/")
    def root():
        index = settings.frontend_dir / "index.html"
        if index.is_file():
            if primary_frontend(settings.frontend_dir):
                return HTMLResponse(render_primary(index), headers={"Cache-Control": "no-cache"})
            return FileResponse(index, media_type="text/html", headers={"Cache-Control": "no-cache"})
        return HTMLResponse("<!doctype html><html lang='en'><title>DepBridge</title><h1>DepBridge</h1>"
                            "<p>Submit a public repository using the CLI or <a href='/docs'>API documentation</a>.</p></html>")

    @app.get("/static/index.html")
    def primary_index_alias():
        return RedirectResponse("/", status_code=307)

    @app.get("/static/start.html")
    def start_alias():
        if primary_frontend(settings.frontend_dir):
            return RedirectResponse("/", status_code=307)
        path = settings.frontend_dir / "static" / "start.html"
        if path.is_file():
            return FileResponse(path, media_type="text/html")
        return RedirectResponse("/", status_code=307)

    app.mount("/service-ui", StaticFiles(directory=ASSETS), name="service-ui")
    static = settings.frontend_dir / "static"
    if primary_frontend(settings.frontend_dir):
        static = settings.frontend_dir
    if static.is_dir():
        app.mount("/static", StaticFiles(directory=static), name="static")
    return app


app = create_app()
