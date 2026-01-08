"""
Health check HTTP server for monitoring and deployment verification.
Provides endpoints for Railway and external monitoring tools.
"""

import asyncio
import logging
import os
from aiohttp import web
from datetime import datetime

logger = logging.getLogger('Herald.Health')

# Global state
_app_ready = False
_bot_instance = None
_startup_time = datetime.utcnow()

def set_ready(ready: bool = True):
    """Mark the bot as ready or not ready"""
    global _app_ready
    _app_ready = ready
    if ready:
        logger.info("✅ Health check: Bot marked as READY")
    else:
        logger.warning("⚠️ Health check: Bot marked as NOT READY")

def set_bot_instance(bot):
    """Store reference to bot instance for health checks"""
    global _bot_instance
    _bot_instance = bot

async def health_handler(request):
    """
    Health check endpoint - returns 200 if all systems operational
    Used by Railway and load balancers to verify the bot is running
    """
    from core.db import _pool
    from core.version import get_version_string, INSTANCE_ID, GIT_BRANCH

    checks = {
        "status": "healthy",
        "version": get_version_string(),
        "instance_id": INSTANCE_ID,
        "branch": GIT_BRANCH,
        "checks": {}
    }

    # Check if bot is connected to Discord
    if _bot_instance and _bot_instance.is_ready():
        checks["checks"]["discord"] = "connected"
        checks["checks"]["guilds"] = len(_bot_instance.guilds)
        checks["checks"]["latency_ms"] = round(_bot_instance.latency * 1000, 2)
    else:
        checks["checks"]["discord"] = "not_connected"
        checks["status"] = "unhealthy"

    # Check database pool
    if _pool is not None:
        checks["checks"]["database"] = "connected"
        checks["checks"]["db_pool_size"] = _pool.get_size()
    else:
        checks["checks"]["database"] = "not_connected"
        checks["status"] = "unhealthy"

    # Determine HTTP status code
    status_code = 200 if checks["status"] == "healthy" else 503

    return web.json_response(checks, status=status_code)

async def ready_handler(request):
    """
    Readiness check endpoint - returns 200 only if startup is complete
    Used to verify deployment succeeded
    """
    from core.version import get_version_string, INSTANCE_ID

    if _app_ready and _bot_instance and _bot_instance.is_ready():
        return web.json_response({
            "ready": True,
            "version": get_version_string(),
            "instance_id": INSTANCE_ID,
            "uptime_seconds": (datetime.utcnow() - _startup_time).total_seconds()
        }, status=200)
    else:
        return web.json_response({
            "ready": False,
            "reason": "Bot not ready" if not _app_ready else "Discord not connected"
        }, status=503)

async def metrics_handler(request):
    """
    Metrics endpoint - returns basic metrics in JSON format
    Can be consumed by monitoring tools
    """
    from core.db import _pool
    from core.version import get_version_string, INSTANCE_ID, GIT_BRANCH

    metrics = {
        "version": get_version_string(),
        "instance_id": INSTANCE_ID,
        "branch": GIT_BRANCH,
        "uptime_seconds": (datetime.utcnow() - _startup_time).total_seconds(),
        "ready": _app_ready,
    }

    # Add Discord metrics if available
    if _bot_instance and _bot_instance.is_ready():
        metrics["discord_connected"] = True
        metrics["discord_latency_ms"] = round(_bot_instance.latency * 1000, 2)
        metrics["guilds_count"] = len(_bot_instance.guilds)
        metrics["users_count"] = len(set(_bot_instance.get_all_members()))
    else:
        metrics["discord_connected"] = False

    # Add database metrics if available
    if _pool is not None:
        metrics["db_connected"] = True
        metrics["db_pool_size"] = _pool.get_size()
        metrics["db_pool_min"] = _pool.get_min_size()
        metrics["db_pool_max"] = _pool.get_max_size()
    else:
        metrics["db_connected"] = False

    return web.json_response(metrics)

async def root_handler(request):
    """Root endpoint - returns bot info"""
    from core.version import get_version_string, INSTANCE_ID

    return web.json_response({
        "name": "Herald - Hunter: The Reckoning 5E Bot",
        "version": get_version_string(),
        "instance_id": INSTANCE_ID,
        "ready": _app_ready,
        "endpoints": {
            "/": "Bot information",
            "/health": "Health check (200 if healthy, 503 if not)",
            "/ready": "Readiness check (200 if startup complete)",
            "/metrics": "Bot metrics in JSON format"
        }
    })

def create_app():
    """Create the aiohttp web application"""
    app = web.Application()
    app.router.add_get('/', root_handler)
    app.router.add_get('/health', health_handler)
    app.router.add_get('/ready', ready_handler)
    app.router.add_get('/metrics', metrics_handler)
    return app

async def start_health_server(port: int = 8080):
    """Start the health check HTTP server"""
    app = create_app()

    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

    logger.info(f"🏥 Health check server started on http://0.0.0.0:{port}")
    logger.info(f"   Endpoints: /health /ready /metrics")

    return runner
