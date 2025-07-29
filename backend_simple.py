"""
Backend API simple pour GSGUI Desktop
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import uvicorn
import asyncio
import json

app = FastAPI(title="GSGUI Simple API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mock data
MOCK_CHALLENGES = [
    {
        "id": "challenge_1",
        "title": "Architecture Photography Challenge",
        "url": "https://gurushots.com/challenge/architecture-photography",
        "votes": 1250,
        "rank": 45,
        "level": "Pro",
        "exposure": "High",
        "gps": "Paris, France",
        "time_left_days": 2,
        "selected_strategy": None,
        "turbo_status": "none"
    },
    {
        "id": "challenge_2", 
        "title": "Street Photography Masters",
        "url": "https://gurushots.com/challenge/street-photography",
        "votes": 890,
        "rank": 78,
        "level": "Expert",
        "exposure": "Medium",
        "gps": "New York, USA",
        "time_left_days": 5,
        "selected_strategy": "fill",
        "turbo_status": "none"
    },
    {
        "id": "challenge_3",
        "title": "Nature's Beauty Contest", 
        "url": "https://gurushots.com/challenge/nature-beauty",
        "votes": 2100,
        "rank": 23,
        "level": "Master",
        "exposure": "Very High",
        "gps": "Amazon, Brazil",
        "time_left_days": 1,
        "selected_strategy": "4m",
        "turbo_status": "completed"
    }
]

# Models
class ProfileRegisterRequest(BaseModel):
    profile_name: str
    gs_token: Optional[str] = None

class ProfileRegisterResponse(BaseModel):
    profile_id: str
    profile_name: str
    status: str
    message: str
    has_valid_token: bool

class ScheduleStrategyRequest(BaseModel):
    challenge_id: str
    strategy_name: str
    challenge_title: Optional[str] = None
    scheduled_at: str

class TurboExecutionRequest(BaseModel):
    challenge_id: str
    challenge_title: Optional[str] = None
    challenge_time_left: Optional[str] = None
    algorithm: Optional[str] = None

class SimpleVoteRequest(BaseModel):
    challenge_url: str
    vote_count: int

# In-memory storage
profiles = {}
strategies = {}
turbo_executions = {}

# Routes
@app.get("/")
async def root():
    return {"message": "GSGUI Simple API", "status": "running"}

@app.post("/api/v1/profiles/register", response_model=ProfileRegisterResponse)
async def register_profile(request: ProfileRegisterRequest):
    """Enregistre un profil"""
    try:
        profile_id = request.profile_name
        profiles[profile_id] = {
            "profile_name": request.profile_name,
            "gs_token": request.gs_token,
            "created_at": datetime.now().isoformat()
        }
        
        return ProfileRegisterResponse(
            profile_id=profile_id,
            profile_name=request.profile_name,
            status="created" if profile_id not in profiles else "existing",
            message="Profile registered successfully",
            has_valid_token=bool(request.gs_token)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/challenges/")
async def get_challenges(user_token: str):
    """Récupère les challenges"""
    try:
        return {"challenges": MOCK_CHALLENGES}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/profiles/{profile_id}/strategies")
async def schedule_strategy(profile_id: str, request: ScheduleStrategyRequest):
    """Programme une stratégie"""
    try:
        strategy_id = f"{profile_id}_{request.challenge_id}_{int(datetime.now().timestamp())}"
        
        strategies[strategy_id] = {
            "strategy_id": strategy_id,
            "profile_id": profile_id,
            "challenge_id": request.challenge_id,
            "strategy_name": request.strategy_name,
            "challenge_title": request.challenge_title,
            "scheduled_at": request.scheduled_at,
            "status": "pending",
            "created_at": datetime.now().isoformat()
        }
        
        # Mettre à jour le challenge mock
        for challenge in MOCK_CHALLENGES:
            if challenge["id"] == request.challenge_id:
                challenge["selected_strategy"] = request.strategy_name
                break
        
        return {
            "strategy_id": strategy_id,
            "message": "Strategy scheduled successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/profiles/{profile_id}/strategies")
async def list_strategies(profile_id: str):
    """Liste les stratégies"""
    try:
        profile_strategies = [s for s in strategies.values() if s["profile_id"] == profile_id]
        return {
            "strategies": profile_strategies,
            "total_count": len(profile_strategies)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/v1/profiles/{profile_id}/strategies/{strategy_id}")
async def cancel_strategy(profile_id: str, strategy_id: str):
    """Annule une stratégie"""
    try:
        if strategy_id in strategies:
            del strategies[strategy_id]
        return {"message": "Strategy cancelled"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/profiles/{profile_id}/turbo/execute")
async def execute_turbo(profile_id: str, request: TurboExecutionRequest):
    """Exécute un turbo"""
    try:
        turbo_id = f"turbo_{profile_id}_{request.challenge_id}_{int(datetime.now().timestamp())}"
        
        turbo_executions[turbo_id] = {
            "turbo_id": turbo_id,
            "profile_id": profile_id,
            "challenge_id": request.challenge_id,
            "challenge_title": request.challenge_title,
            "algorithm_used": request.algorithm or "hybrid",
            "execution_started_at": datetime.now().isoformat(),
            "status": "running",
            "success": True,
            "pairs_processed": 10,
            "successful_pairs": 8
        }
        
        # Simuler l'exécution
        await asyncio.sleep(0.1)
        
        # Mettre à jour le challenge mock
        for challenge in MOCK_CHALLENGES:
            if challenge["id"] == request.challenge_id:
                challenge["turbo_status"] = "running"
                break
        
        return {
            "turbo_id": turbo_id,
            "profile_id": profile_id,
            "challenge_id": request.challenge_id,
            "status": "running",
            "message": "Turbo execution started"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/challenges/simple-vote")
async def simple_vote(request: SimpleVoteRequest, user_token: str):
    """Vote simple"""
    try:
        # Simuler le vote
        await asyncio.sleep(0.1)
        
        return {
            "success": True,
            "message": f"Successfully cast {request.vote_count} votes",
            "result_data": {
                "votes_cast": request.vote_count,
                "challenge_url": request.challenge_url
            }
        }
    except Exception as e:
        return {
            "success": False,
            "message": str(e),
            "result_data": {}
        }

# Utility functions
async def cancel_challenge_strategies_impl(profile_id: str, challenge_id: str) -> int:
    """Annule toutes les stratégies d'un challenge"""
    cancelled = 0
    to_remove = []
    
    for strategy_id, strategy in strategies.items():
        if strategy["profile_id"] == profile_id and strategy["challenge_id"] == challenge_id:
            to_remove.append(strategy_id)
            cancelled += 1
    
    for strategy_id in to_remove:
        del strategies[strategy_id]
    
    return cancelled

if __name__ == "__main__":
    print("🚀 Démarrage du backend GSGUI Simple...")
    uvicorn.run(app, host="127.0.0.1", port=8001, log_level="info")