"""
API Router v1 - Regroupe tous les endpoints
"""

from fastapi import APIRouter

from app.api.v1.endpoints import challenges, profiles, strategies, turbo, logs, swap_and_tracking, anca_strategies, simple_extensions

api_router = APIRouter()

# Inclure tous les routers d'endpoints
api_router.include_router(
    challenges.router,
    prefix="/challenges",
    tags=["challenges"]
)

api_router.include_router(
    profiles.router,
    prefix="/profiles",
    tags=["profiles"]
)

api_router.include_router(
    strategies.router,
    prefix="",
    tags=["strategies"]
)

api_router.include_router(
    turbo.router,
    prefix="",
    tags=["turbo"]
)

api_router.include_router(
    logs.router,
    prefix="",
    tags=["logs"]
)

api_router.include_router(
    swap_and_tracking.router,
    prefix="/swap-tracking",
    tags=["swap-tracking"]
)

api_router.include_router(
    anca_strategies.router,
    prefix="/anca",
    tags=["anca-intelligence"]
)

api_router.include_router(
    simple_extensions.router,
    prefix="/simple",
    tags=["simple-anca-strategies"]
)