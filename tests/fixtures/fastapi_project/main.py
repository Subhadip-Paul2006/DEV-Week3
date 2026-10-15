"""Main entry point for the FastAPI test fixture application.

Demonstrates comprehensive system design concepts:
- OpenAPI documentation & client-server endpoints
- CORS middleware
- Health check endpoints
- Error handling middleware & custom exception handlers
- Real-time WebSockets
"""

from __future__ import annotations

import time

from fastapi import FastAPI, HTTPException, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import settings
from .observability import HTTP_REQUESTS_TOTAL, REQUEST_DURATION_SECONDS, logger
from .routes import router as orders_router

# 1. FastAPI Application with OpenAPI metadata
app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Production-grade FastAPI fixture demonstrating system design patterns.",
    openapi_url="/api/v1/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

# 2. Security: CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://dashboard.example.com", "https://admin.example.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)


# 3. Observability & Performance: Request Timing Middleware
@app.middleware("http")
async def monitor_requests_middleware(request: Request, call_next):
    """Record metrics, request latency, and structured logging."""
    start_time = time.time()
    method = request.method
    endpoint = request.url.path

    try:
        response: Response = await call_next(request)
        duration = time.time() - start_time
        REQUEST_DURATION_SECONDS.labels(method=method, endpoint=endpoint).observe(duration)
        HTTP_REQUESTS_TOTAL.labels(method=method, endpoint=endpoint, status_code=response.status_code).inc()
        return response
    except Exception as exc:
        duration = time.time() - start_time
        HTTP_REQUESTS_TOTAL.labels(method=method, endpoint=endpoint, status_code=500).inc()
        logger.error(f"Unhandled server error on {endpoint}: {exc}", exc_info=True)
        raise exc


# 4. Foundation: Error Handling with Custom Exception Handlers
@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    """Standardized JSON format for HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.status_code, "message": exc.detail, "path": str(request.url.path)}},
    )


# 5. Deployment: Health Checks & Readiness Probes
@app.get("/health", tags=["system"])
@app.get("/healthz", tags=["system"])
def health_check():
    """Liveness probe indicating process is healthy."""
    return {"status": "ok", "service": settings.app_name}


@app.get("/ready", tags=["system"])
def readiness_check():
    """Readiness probe indicating application dependencies are accessible."""
    return {
        "status": "ready",
        "environment": settings.environment,
        "database": "connected",
        "cache": "connected",
    }


# 6. Streaming: Real-time WebSockets
@app.websocket("/ws/notifications")
async def websocket_notifications_endpoint(websocket: WebSocket):
    """Real-time bi-directional notifications stream."""
    await websocket.accept()
    logger.info("WebSocket connection established")
    try:
        while True:
            data = await websocket.receive_text()
            # Echo heartbeat or notification
            await websocket.send_text(f"ACK: {data}")
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")


# Mount feature routes
app.include_router(orders_router)
