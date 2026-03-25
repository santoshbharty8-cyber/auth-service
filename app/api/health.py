from datetime import datetime, UTC
from fastapi import APIRouter, HTTPException
from app.core.health_checks import check_database, check_redis
import app.core.startup_state as startup_state
from app.schemas.health_schema import ReadinessResponse

router = APIRouter(tags=["Health"])


@router.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "auth-system",
        "timestamp": datetime.now(UTC)
    }


@router.get("/live")
def liveness_probe():
    return {
        "status": "alive"
    }


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    responses={503: {"description": "Service not ready"}}
)
def readiness_probe():

    # 🔹 Step 1: Check app startup
    if not startup_state.startup_complete:
        raise HTTPException(
            status_code=503,
            detail="Service starting"
        )

    # 🔹 Step 2: Dependency checks (SAFE)
    try:
        checks = {
            "database": check_database(),
            "redis": check_redis()
        }
    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Dependency check failed"
        )

    # 🔹 Step 3: Validate all dependencies
    if not all(checks.values()):
        raise HTTPException(
            status_code=503,
            detail={
                "status": "not_ready",
                "checks": checks
            }
        )

    return {
        "status": "ready",
        "checks": checks
    }