"""
FastAPI Main Application Entry Point.
"""
import uuid
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from app.api.routes import router
from app.core.config import settings
from app.core.logging import setup_logging, logger
from storage.db.connection import db


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("Initializing TRUST-TWIN Foundation Services...")
    db.init_db()
    logger.info("FastAPI ready and listening.")
    yield
    logger.info("Shutting down TRUST-TWIN...")


app = FastAPI(
    title="SkyGuard AI API",
    description="Real-Time Explainable Anomaly Detection and Sensor Health Monitoring for Automatic Weather Stations (SIH26073)",
    version=settings.app_version,
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    start_time = time.time()
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = f"{process_time:.4f}"
    response.headers["X-Request-ID"] = request_id
    return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Uniform error envelope: {error: {code, message, details, request_id}}
    """
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Payload validation failed",
                "details": exc.errors(),
                "request_id": request_id,
            }
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    logger.error(f"Unhandled error [{request_id}]: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred. Please try again or contact support.",
                "request_id": request_id,
            }
        },
    )


app.include_router(router)
