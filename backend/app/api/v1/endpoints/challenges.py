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
from app.schemas.turbo import (
    TurboExecutionRequest,
    TurboExecutionResponse
)
from app.services.gurushots_api import GuruShotsAPI, ChallengeData
from app.services.turbo_executor import turbo_executor
from app.websockets.connection_manager import connection_manager
from app.models.file_based_models import User, Challenge

logger = logging.getLogger(__name__)

router = APIRouter()


# Dependency pour obtenir l'utilisateur
async def get_current_user(user_token: str = Query(..., description="GuruShots user token")) -> User:
    """Récupère et valide l'utilisateur par son token"""
    if not user_token:
        raise HTTPException(status_code=400, detail="User token is required")
    
    # Chercher l'utilisateur par token
    user = User.get_by_token(user_token)
    if not user:
        # Si l'utilisateur n'existe pas, on pourrait le créer automatiquement
        # ou retourner une erreur. Pour l'instant, créons-le automatiquement
        user_id = user_token[:10]  # Utiliser une partie du token comme ID
        user = User.create(
            user_id=user_id,
            username=f"user_{user_id}",
            xtoken=user_token
        )
        if not user:
            raise HTTPException(status_code=500, detail="Could not create user")
    
    return user


@router.get("/", response_model=ChallengeListResponse)
async def get_challenges(
    current_user: User = Depends(get_current_user),
    page: int = Query(1, ge=1),
    per_page: int = Query(100, ge=1, le=500)
):
    """
    Récupère la liste des challenges actifs
    Équivalent de fetch_challenges() dans gsui.py
    """
    try:
        logger.info(f"🔍 Fetching challenges for user: {current_user.username}")
        
        # Créer le client API
        api_client = GuruShotsAPI(current_user.xtoken)
        
        # Récupérer les challenges depuis l'API
        challenges_data = await api_client.get_challenges()
        
        # Récupérer les challenges sauvegardés pour cet utilisateur
        saved_challenges = current_user.get_challenges()
        
        # Convertir en format API response et sauvegarder
        challenges = []
        for challenge_data in challenges_data:
            # Créer le modèle Challenge
            challenge = Challenge.create_from_api_data(
                user_id=current_user.id,
                api_challenge_data={
                    'id': challenge_data.id,
                    'title': challenge_data.title,
                    'url': challenge_data.url,
                    'end_time': challenge_data.end_time,
                    'time_left': challenge_data.time_left,
                    'votes': challenge_data.votes,
                    'rank': challenge_data.rank,
                    'level': challenge_data.level,
                    'exposure': challenge_data.exposure,
                    'gps': challenge_data.gps
                }
            )
            
            # Récupérer les infos sauvegardées si elles existent
            saved_info = saved_challenges.get(challenge.id, {})
            if saved_info:
                challenge.selected_strategy = saved_info.get('strategy_name')
                challenge.status = saved_info.get('status', 'active')
            else:
                challenge.status = 'active'
            
            # Sauvegarder/mettre à jour le challenge
            challenge.save()
            
            # Convertir en ChallengeResponse
            challenge_response = ChallengeResponse(
                id=challenge.id,
                title=challenge.title,
                url=challenge.url,
                end_time=challenge.end_time,
                time_left_days=challenge.time_left_days,
                time_left_hours=challenge.time_left_hours,
                time_left_minutes=challenge.time_left_minutes,
                time_left_seconds=challenge.time_left_seconds,
                votes=challenge.votes,
                rank=challenge.rank,
                level=challenge.level,
                exposure=challenge.exposure,
                gps=challenge.gps,
                selected_strategy=challenge.selected_strategy,
                status=challenge.status,
                turbo_status=challenge.turbo_status,
                current_process_id=challenge.current_process_id,
                created_at=datetime.fromisoformat(challenge.created_at or datetime.now().isoformat()),
                updated_at=datetime.fromisoformat(challenge.updated_at or datetime.now().isoformat()),
                user_id=challenge.user_id
            )
            challenges.append(challenge_response)
        
        # Pagination simple
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
        
        # Notifier via WebSocket
        await connection_manager.notify_challenge_update(
            current_user.id, 
            {"challenges_count": len(challenges)}
        )
        
        return response
        
    except Exception as e:
        logger.error(f"❌ Error fetching challenges: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching challenges: {str(e)}")


@router.post("/vote-panel", response_model=VotePanelResponse)
async def get_vote_panel(
    request: VotePanelRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Récupère le panel de vote pour un challenge
    Équivalent de fetch_get_votes_panel() dans gsui.py
    """
    try:
        logger.info(f"🗳️ Getting vote panel for: {request.challenge_url}")
        
        # Créer le client API
        api_client = GuruShotsAPI(current_user.xtoken)
        
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
    current_user: User = Depends(get_current_user)
):
    """
    Soumet des votes pour un challenge
    Équivalent de fetch_post_votes_panel() dans gsui.py
    """
    try:
        logger.info(f"🗳️ Submitting {len(request.vote_tokens)} votes for challenge {request.challenge_id}")
        
        # Créer le client API
        api_client = GuruShotsAPI(current_user.xtoken)
        
        # Soumettre les votes
        vote_result = await api_client.submit_votes(request.challenge_id, request.vote_tokens)
        
        response = VoteResponse(
            success=vote_result.success,
            message=vote_result.message,
            result_data=vote_result.result_data
        )
        
        # Notifier via WebSocket
        await connection_manager.notify_vote_executed(
            current_user.id,
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
    current_user: User = Depends(get_current_user)
):
    """
    Exécute un vote simple (récupère le panel et vote automatiquement)
    Équivalent des fonctions de vote dans gsui.py
    """
    try:
        logger.info(f"🚀 Executing simple vote: {request.vote_count} votes for {request.challenge_url}")
        
        # Créer le client API
        api_client = GuruShotsAPI(current_user.xtoken)
        
        # Exécuter le vote simple
        vote_result = await api_client.execute_simple_vote(request.challenge_url, request.vote_count)
        
        response = VoteResponse(
            success=vote_result.success,
            message=vote_result.message,
            result_data=vote_result.result_data
        )
        
        # Notifier via WebSocket
        challenge_id = request.challenge_url.split('/')[-1] if '/' in request.challenge_url else "unknown"
        await connection_manager.notify_vote_executed(
            current_user.id,
            challenge_id,
            request.vote_count,
            vote_result.success
        )
        
        logger.info(f"✅ Simple vote executed: success={vote_result.success}")
        return response
        
    except Exception as e:
        logger.error(f"❌ Error executing simple vote: {e}")
        raise HTTPException(status_code=500, detail=f"Error executing simple vote: {str(e)}")


@router.get("/by-url")
async def get_challenge_by_url(
    challenge_url: str = Query(..., description="URL slug du challenge, ex: frame-it-4"),
    current_user: User = Depends(get_current_user)
):
    """Récupère les infos d'un challenge (id, title, url) depuis son URL slug via get_challenge."""
    try:
        api_client = GuruShotsAPI(current_user.xtoken)
        data = await api_client.get_challenge_details(challenge_url.strip())

        if not data or data.get('error'):
            raise HTTPException(status_code=404, detail=f"Challenge '{challenge_url}' introuvable")

        challenge = data.get('challenge', {})
        challenge_id = challenge.get('id')
        title = challenge.get('title') or challenge_url

        if not challenge_id:
            raise HTTPException(status_code=404, detail=f"Challenge '{challenge_url}' introuvable")

        return {'id': str(challenge_id), 'title': title, 'url': challenge.get('url', challenge_url)}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting challenge by url '{challenge_url}': {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{challenge_id}")
async def get_challenge(
    challenge_id: str,
    current_user: User = Depends(get_current_user)
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
    current_user: User = Depends(get_current_user)
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
    current_user: User = Depends(get_current_user)
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


@router.post("/turbo", response_model=TurboExecutionResponse)
async def execute_turbo(
    request: TurboExecutionRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Exécute un turbo complet pour un challenge
    Équivalent de la fonctionnalité turbo complète dans gsui.py
    """
    try:
        import uuid
        from datetime import datetime
        
        # Générer un ID unique pour ce turbo
        turbo_id = str(uuid.uuid4())

        # Logs désactivés pour réduire le bruit
        # logger.info(f"🚀 Démarrage turbo {turbo_id} pour challenge {request.challenge_id}")
        # logger.info(f"   Algorithme: {request.algorithm or 'hybrid'}")
        
        # Exécuter le turbo
        result = await turbo_executor.execute_turbo(
            profile_id=current_user.id,
            turbo_id=turbo_id,
            challenge_id=request.challenge_id,
            challenge_title=request.challenge_title,
            challenge_time_left=request.challenge_time_left,
            algorithm=request.algorithm or "hybrid",
            xtoken=current_user.xtoken
        )
        
        # Construire la réponse
        response = TurboExecutionResponse(
            turbo_id=turbo_id,
            profile_id=current_user.id,
            challenge_id=request.challenge_id,
            challenge_title=request.challenge_title or f"Challenge {request.challenge_id}",
            algorithm_used=request.algorithm or "hybrid",
            execution_started_at=datetime.now(),
            execution_completed_at=datetime.now(),
            status="completed" if result.get('success', False) else "failed",
            success=result.get('success', False),
            pairs_processed=result.get('pairs_processed', 0),
            successful_pairs=result.get('successful_pairs', 0),
            failed_pairs=result.get('failed_pairs', 0),
            error_message=None if result.get('success', False) else "Turbo execution failed",
            result_data=result
        )
        
        logger.info(f"✅ Turbo {turbo_id} terminé: success={result.get('success', False)}")
        
        # Notifier via WebSocket
        await connection_manager.notify_turbo_completed(
            current_user.id,
            turbo_id,
            result
        )
        
        return response
        
    except Exception as e:
        logger.error(f"❌ Error executing turbo: {e}")
        raise HTTPException(status_code=500, detail=f"Error executing turbo: {str(e)}")


# ============================================================================
# AUTO-REFRESH ENDPOINTS
# ============================================================================

@router.post("/{profile_id}/auto-refresh/toggle")
async def toggle_auto_refresh(
    profile_id: str,
    enabled: bool = Query(..., description="Enable or disable auto-refresh"),
    interval_minutes: int = Query(10, ge=1, le=60, description="Refresh interval in minutes (1-60)")
):
    """
    Active/désactive l'auto-refresh global pour un profil

    Args:
        profile_id: ID du profil
        enabled: True pour activer, False pour désactiver
        interval_minutes: Intervalle de rafraîchissement en minutes (défaut: 10)

    Returns:
        Statut de l'auto-refresh avec prochaine exécution
    """
    try:
        from app.services.auto_refresh_scheduler import auto_refresh_scheduler

        if auto_refresh_scheduler is None:
            raise HTTPException(
                status_code=503,
                detail="Auto-refresh scheduler not initialized"
            )

        if enabled:
            success = await auto_refresh_scheduler.enable_auto_refresh(
                profile_id, interval_minutes
            )
        else:
            success = await auto_refresh_scheduler.disable_auto_refresh(profile_id)

        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to toggle auto-refresh"
            )

        status = auto_refresh_scheduler.get_status(profile_id)

        return {
            "success": True,
            "profile_id": profile_id,
            **status
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error toggling auto-refresh: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{profile_id}/auto-refresh/status")
async def get_auto_refresh_status(profile_id: str):
    """
    Récupère le statut de l'auto-refresh pour un profil

    Args:
        profile_id: ID du profil

    Returns:
        Statut actuel de l'auto-refresh
    """
    try:
        from app.services.auto_refresh_scheduler import auto_refresh_scheduler

        if auto_refresh_scheduler is None:
            raise HTTPException(
                status_code=503,
                detail="Auto-refresh scheduler not initialized"
            )

        status = auto_refresh_scheduler.get_status(profile_id)

        return {
            "success": True,
            "profile_id": profile_id,
            **status
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting auto-refresh status: {e}")
        raise HTTPException(status_code=500, detail=str(e))