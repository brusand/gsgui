"""
Challenge API endpoints - Basé sur la logique de gsui.py
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

from app.schemas.challenge import (
    ChallengeResponse,
    ChallengeListResponse,
    VotePanelRequest,
    VotePanelResponse,
    VoteRequest,
    SimpleVoteRequest,
    VoteResponse
)
from app.services.gurushots_api import GuruShotsAPI, ChallengeData
from app.websockets.connection_manager import connection_manager

logger = logging.getLogger(__name__)

router = APIRouter()


# Dependency pour obtenir le token utilisateur
async def get_user_token(user_token: str = Query(..., description="GuruShots user token")) -> str:
    """Récupère et valide le token utilisateur"""
    if not user_token:
        raise HTTPException(status_code=400, detail="User token is required")
    return user_token


@router.get("/", response_model=ChallengeListResponse)
async def get_challenges(
    user_token: str = Depends(get_user_token),
    page: int = Query(1, ge=1),
    per_page: int = Query(100, ge=1, le=500)
):
    """
    Récupère la liste des challenges actifs
    Équivalent de fetch_challenges() dans gsui.py
    """
    try:
        logger.info(f"🔍 Fetching challenges for user token: {user_token[:20]}...")
        
        # Créer le client API
        api_client = GuruShotsAPI(user_token)
        
        # Récupérer les challenges
        challenges_data = await api_client.get_challenges()
        
        # Convertir en format API response
        challenges = []
        for challenge_data in challenges_data:
            challenge_response = ChallengeResponse(
                id=challenge_data.id,
                title=challenge_data.title,
                url=challenge_data.url,
                end_time=challenge_data.end_time,
                time_left_days=challenge_data.time_left.get("days", 0),
                time_left_hours=challenge_data.time_left.get("hours", 0),
                time_left_minutes=challenge_data.time_left.get("minutes", 0),
                time_left_seconds=challenge_data.time_left.get("seconds", 0),
                votes=challenge_data.votes,
                rank=challenge_data.rank,
                level=challenge_data.level,
                exposure=challenge_data.exposure,
                gps=challenge_data.gps,
                selected_strategy=None,
                status="active",
                turbo_status="",
                current_process_id=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                user_id=user_token[:10]  # Utiliser une partie du token comme user_id temporaire
            )
            challenges.append(challenge_response)
        
        # Pagination simple (TODO: améliorer avec une vraie pagination)
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_challenges = challenges[start_idx:end_idx]
        
        response = ChallengeListResponse(
            challenges=paginated_challenges,
            total=len(challenges),
            page=page,
            per_page=per_page
        )
        
        logger.info(f"✅ Successfully returned {len(paginated_challenges)} challenges")
        
        # Notifier via WebSocket (si utilisateur connecté)
        user_id = user_token[:10]  # Utiliser une partie du token comme user_id
        await connection_manager.notify_challenge_update(
            user_id, 
            {"challenges_count": len(challenges)}
        )
        
        return response
        
    except Exception as e:
        logger.error(f"❌ Error fetching challenges: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching challenges: {str(e)}")


@router.post("/vote-panel", response_model=VotePanelResponse)
async def get_vote_panel(
    request: VotePanelRequest,
    user_token: str = Depends(get_user_token)
):
    """
    Récupère le panel de vote pour un challenge
    Équivalent de fetch_get_votes_panel() dans gsui.py
    """
    try:
        logger.info(f"🗳️ Getting vote panel for: {request.challenge_url}")
        
        # Créer le client API
        api_client = GuruShotsAPI(user_token)
        
        # Récupérer le panel de vote
        vote_panel = await api_client.get_vote_panel(request.challenge_url, request.limit)
        
        response = VotePanelResponse(
            success=vote_panel.success,
            message=vote_panel.message,
            images=vote_panel.images,
            challenge_data=vote_panel.challenge_data
        )
        
        logger.info(f"✅ Vote panel retrieved: {len(vote_panel.images)} images")
        return response
        
    except Exception as e:
        logger.error(f"❌ Error getting vote panel: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting vote panel: {str(e)}")


@router.post("/vote", response_model=VoteResponse)
async def submit_votes(
    request: VoteRequest,
    user_token: str = Depends(get_user_token)
):
    """
    Soumet des votes pour un challenge
    Équivalent de fetch_post_votes_panel() dans gsui.py
    """
    try:
        logger.info(f"🗳️ Submitting {len(request.vote_tokens)} votes for challenge {request.challenge_id}")
        
        # Créer le client API
        api_client = GuruShotsAPI(user_token)
        
        # Soumettre les votes
        vote_result = await api_client.submit_votes(request.challenge_id, request.vote_tokens)
        
        response = VoteResponse(
            success=vote_result.success,
            message=vote_result.message,
            result_data=vote_result.result_data
        )
        
        # Notifier via WebSocket
        user_id = user_token[:10]
        await connection_manager.notify_vote_executed(
            user_id,
            request.challenge_id,
            len(request.vote_tokens),
            vote_result.success
        )
        
        logger.info(f"✅ Votes submitted: success={vote_result.success}")
        return response
        
    except Exception as e:
        logger.error(f"❌ Error submitting votes: {e}")
        raise HTTPException(status_code=500, detail=f"Error submitting votes: {str(e)}")


@router.post("/simple-vote", response_model=VoteResponse)
async def execute_simple_vote(
    request: SimpleVoteRequest,
    user_token: str = Depends(get_user_token)
):
    """
    Exécute un vote simple (récupère le panel et vote automatiquement)
    Équivalent des fonctions de vote dans gsui.py
    """
    try:
        logger.info(f"🚀 Executing simple vote: {request.vote_count} votes for {request.challenge_url}")
        
        # Créer le client API
        api_client = GuruShotsAPI(user_token)
        
        # Exécuter le vote simple
        vote_result = await api_client.execute_simple_vote(request.challenge_url, request.vote_count)
        
        response = VoteResponse(
            success=vote_result.success,
            message=vote_result.message,
            result_data=vote_result.result_data
        )
        
        # Notifier via WebSocket
        user_id = user_token[:10]
        challenge_id = request.challenge_url.split('/')[-1] if '/' in request.challenge_url else "unknown"
        await connection_manager.notify_vote_executed(
            user_id,
            challenge_id,
            request.vote_count,
            vote_result.success
        )
        
        logger.info(f"✅ Simple vote executed: success={vote_result.success}")
        return response
        
    except Exception as e:
        logger.error(f"❌ Error executing simple vote: {e}")
        raise HTTPException(status_code=500, detail=f"Error executing simple vote: {str(e)}")


@router.get("/{challenge_id}")
async def get_challenge(
    challenge_id: str,
    user_token: str = Depends(get_user_token)
):
    """Récupère les détails d'un challenge spécifique"""
    try:
        # TODO: Implémenter la récupération d'un challenge spécifique
        # Pour l'instant, retourner une erreur not implemented
        raise HTTPException(status_code=501, detail="Not implemented yet")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting challenge {challenge_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting challenge: {str(e)}")


@router.put("/{challenge_id}")
async def update_challenge(
    challenge_id: str,
    user_token: str = Depends(get_user_token)
):
    """Met à jour un challenge (stratégie, statut, etc.)"""
    try:
        # TODO: Implémenter la mise à jour de challenge
        raise HTTPException(status_code=501, detail="Not implemented yet")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error updating challenge {challenge_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error updating challenge: {str(e)}")


@router.delete("/{challenge_id}")
async def delete_challenge(
    challenge_id: str,
    user_token: str = Depends(get_user_token)
):
    """Supprime un challenge (annule les stratégies associées)"""
    try:
        # TODO: Implémenter la suppression/annulation de challenge
        raise HTTPException(status_code=501, detail="Not implemented yet")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error deleting challenge {challenge_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error deleting challenge: {str(e)}")