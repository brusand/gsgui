"""
API Router v1 - Regroupe tous les endpoints
"""

from fastapi import APIRouter

from app.api.v1.endpoints import challenges

api_router = APIRouter()

# Inclure tous les routers d'endpoints
api_router.include_router(
    challenges.router,
    prefix="/challenges",
    tags=["challenges"]
)