"""
Turbo API endpoints - Migration from gsui.py turbo system
"""

from fastapi import APIRouter, HTTPException, Depends, Query, Path, BackgroundTasks
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime
import uuid
import asyncio

from app.schemas.turbo import (
    TurboExecutionRequest,
    TurboExecutionResponse,
    TurboStatusResponse,
    TurboHistoryResponse,
    TurboHistoryEntry,
    TurboSettingsResponse,
    TurboSettingsUpdateRequest,
    TurboStatisticsResponse,
    AvailableAlgorithmsResponse,
    TurboLogEntry,
    TurboPairComparison
)
from app.services.config_manager import config_manager
from app.services.turbo_executor import turbo_executor
from app.websockets.connection_manager import connection_manager
from app.websockets.turbo_notifications import *

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/{profile_id}/turbo/execute", response_model=TurboExecutionResponse)
async def execute_turbo(
    profile_id: str = Path(..., description="Profile ID"),
    request: TurboExecutionRequest = ...,
    background_tasks: BackgroundTasks = ...
):
    """
    Exécute le turbo pour un challenge
    Équivalent de turbo_challenge() dans gsui.py
    """
    try:
        logger.info(f"🚀 Turbo execution request for profile {profile_id}, challenge {request.challenge_id}")
        
        # Vérifier que le profil existe
        user = config_manager.get_user(profile_id)
        if not user:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        # Vérifier que le profil a un token valide
        xtoken = user.get('xtoken')
        if not xtoken:
            raise HTTPException(status_code=400, detail="Profile has no valid GuruShots token")
        
        # Générer un ID unique pour cette exécution turbo
        turbo_id = f"turbo_{profile_id}_{request.challenge_id}_{int(datetime.now().timestamp())}"
        
        # Récupérer l'algorithme à utiliser
        algorithm = request.algorithm or user.get('turbo_algorithm', '[hybrid,position_aware,adaptive_time]')
        
        # Créer la réponse initiale
        response = TurboExecutionResponse(
            turbo_id=turbo_id,
            profile_id=profile_id,
            challenge_id=request.challenge_id,
            challenge_title=request.challenge_title,
            algorithm_used=algorithm,
            execution_started_at=datetime.now(),
            status='running',
            pairs_processed=0,
            successful_pairs=0,
            failed_pairs=0
        )
        
        # Sauvegarder le statut initial
        await _save_turbo_status(profile_id, turbo_id, response.dict())
        
        # Lancer l'exécution en arrière-plan
        background_tasks.add_task(
            _execute_turbo_background,
            profile_id=profile_id,
            turbo_id=turbo_id,
            request=request,
            algorithm=algorithm,
            xtoken=xtoken
        )
        
        # Notifier via WebSocket du démarrage
        await connection_manager.notify_turbo_started(profile_id, response.dict())
        
        logger.info(f"✅ Turbo execution started: {turbo_id}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting turbo execution: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start turbo execution: {str(e)}")


@router.get("/{profile_id}/turbo/status/{challenge_id}", response_model=TurboStatusResponse)
async def get_turbo_status(
    profile_id: str = Path(..., description="Profile ID"),
    challenge_id: str = Path(..., description="Challenge ID")
):
    """Récupère le statut turbo actuel pour un challenge"""
    try:
        # Vérifier que le profil existe
        user = config_manager.get_user(profile_id)
        if not user:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        # Récupérer le statut turbo depuis la configuration
        turbo_statuses = config_manager.get_user_section(profile_id, 'turbo_status') or {}
        turbo_status_key = f"{challenge_id}_current"
        turbo_data = turbo_statuses.get(turbo_status_key, {})
        
        if not turbo_data:
            # Pas de turbo en cours
            return TurboStatusResponse(
                profile_id=profile_id,
                challenge_id=challenge_id,
                status='none'
            )
        
        response = TurboStatusResponse(
            turbo_id=turbo_data.get('turbo_id'),
            profile_id=profile_id,
            challenge_id=challenge_id,
            status=turbo_data.get('status', 'none'),
            algorithm_used=turbo_data.get('algorithm_used'),
            execution_started_at=datetime.fromisoformat(turbo_data.get('execution_started_at')) if turbo_data.get('execution_started_at') else None,
            execution_completed_at=datetime.fromisoformat(turbo_data.get('execution_completed_at')) if turbo_data.get('execution_completed_at') else None,
            pairs_processed=turbo_data.get('pairs_processed', 0),
            successful_pairs=turbo_data.get('successful_pairs', 0),
            failed_pairs=turbo_data.get('failed_pairs', 0),
            success=turbo_data.get('success', False)
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting turbo status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get turbo status")


@router.get("/{profile_id}/turbo/history", response_model=TurboHistoryResponse)
async def get_turbo_history(
    profile_id: str = Path(..., description="Profile ID"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0)
):
    """
    Récupère l'historique turbo pour un profil
    Équivalent des données de turbo_history dans gsui.py
    """
    try:
        logger.info(f"📋 Getting turbo history for profile {profile_id}")
        
        # Vérifier que le profil existe
        user = config_manager.get_user(profile_id)
        if not user:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        # Récupérer l'historique turbo
        turbo_history = config_manager.get_user_section(profile_id, 'turbo_history') or {}
        
        entries = []
        success_count = 0
        failed_count = 0
        
        # Convertir les données d'historique
        for turbo_id, turbo_data in turbo_history.items():
            try:
                success = turbo_data.get('success', False)
                if success:
                    success_count += 1
                else:
                    failed_count += 1
                
                entry = TurboHistoryEntry(
                    turbo_id=turbo_id,
                    profile_id=profile_id,
                    challenge_id=turbo_data.get('challenge_id', ''),
                    challenge_title=turbo_data.get('challenge_title', ''),
                    timestamp=datetime.fromisoformat(turbo_data.get('timestamp', datetime.now().isoformat())),
                    time_left=turbo_data.get('time_left', ''),
                    algorithm=turbo_data.get('algorithm', 'unknown'),
                    strategy_description=turbo_data.get('strategy_description', ''),
                    success=success,
                    pairs_processed=turbo_data.get('pairs_processed', 0),
                    successful_pairs=turbo_data.get('successful_pairs', 0),
                    photo_pairs=turbo_data.get('photo_pairs', []),
                    execution_duration=turbo_data.get('execution_duration'),
                    boost=turbo_data.get('boost')
                )
                entries.append(entry)
                
            except Exception as e:
                logger.warning(f"Error processing turbo history entry {turbo_id}: {e}")
                continue
        
        # Trier par timestamp (plus récent en premier)
        entries.sort(key=lambda x: x.timestamp, reverse=True)
        
        # Appliquer pagination
        total_count = len(entries)
        paginated_entries = entries[offset:offset + limit]
        
        # Calculer le taux de réussite moyen
        average_success_rate = 0.0
        if total_count > 0:
            average_success_rate = success_count / total_count
        
        response = TurboHistoryResponse(
            entries=paginated_entries,
            total_count=total_count,
            success_count=success_count,
            failed_count=failed_count,
            average_success_rate=average_success_rate
        )
        
        logger.info(f"✅ Retrieved {len(paginated_entries)} turbo history entries for profile {profile_id}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting turbo history for {profile_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get turbo history")


@router.get("/{profile_id}/turbo/settings", response_model=TurboSettingsResponse)
async def get_turbo_settings(
    profile_id: str = Path(..., description="Profile ID")
):
    """Récupère les paramètres turbo d'un profil"""
    try:
        # Vérifier que le profil existe
        user = config_manager.get_user(profile_id)
        if not user:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        # Récupérer les statistiques turbo
        turbo_history = config_manager.get_user_section(profile_id, 'turbo_history') or {}
        total_turbos = len(turbo_history)
        successful_turbos = sum(1 for t in turbo_history.values() if t.get('success', False))
        
        statistics = {
            'total_turbos': total_turbos,
            'successful_turbos': successful_turbos,
            'success_rate': successful_turbos / total_turbos if total_turbos > 0 else 0.0
        }
        
        response = TurboSettingsResponse(
            profile_id=profile_id,
            algorithm=user.get('turbo_algorithm', '[hybrid,position_aware,adaptive_time]'),
            auto_optimize_enabled=user.get('auto_optimize_turbo', False),
            history_enabled=user.get('turbo_history_enabled', True),
            statistics=statistics
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting turbo settings for {profile_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get turbo settings")


@router.put("/{profile_id}/turbo/settings", response_model=TurboSettingsResponse)
async def update_turbo_settings(
    profile_id: str = Path(..., description="Profile ID"),
    updates: TurboSettingsUpdateRequest = ...
):
    """Met à jour les paramètres turbo d'un profil"""
    try:
        logger.info(f"🔄 Updating turbo settings for profile {profile_id}")
        
        # Vérifier que le profil existe
        user = config_manager.get_user(profile_id)
        if not user:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        # Préparer les mises à jour
        update_data = {}
        
        if updates.algorithm is not None:
            update_data['turbo_algorithm'] = updates.algorithm
            
        if updates.auto_optimize_enabled is not None:
            update_data['auto_optimize_turbo'] = updates.auto_optimize_enabled
            
        if updates.history_enabled is not None:
            update_data['turbo_history_enabled'] = updates.history_enabled
        
        if update_data:
            update_data['updated_at'] = datetime.now().isoformat()
            success = config_manager.update_user(profile_id, update_data)
            
            if not success:
                raise HTTPException(status_code=500, detail="Failed to update turbo settings")
        
        # Retourner les paramètres mis à jour
        return await get_turbo_settings(profile_id)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating turbo settings for {profile_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update turbo settings")


@router.get("/{profile_id}/turbo/statistics", response_model=TurboStatisticsResponse)
async def get_turbo_statistics(
    profile_id: str = Path(..., description="Profile ID")
):
    """Récupère les statistiques détaillées turbo"""
    try:
        # Vérifier que le profil existe
        user = config_manager.get_user(profile_id)
        if not user:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        # Récupérer l'historique turbo
        turbo_history = config_manager.get_user_section(profile_id, 'turbo_history') or {}
        
        total_turbos = len(turbo_history)
        successful_turbos = sum(1 for t in turbo_history.values() if t.get('success', False))
        failed_turbos = total_turbos - successful_turbos
        success_rate = successful_turbos / total_turbos if total_turbos > 0 else 0.0
        
        # Calculer la performance par algorithme
        algorithm_performance = {}
        total_pairs = 0
        
        for turbo_data in turbo_history.values():
            algorithm = turbo_data.get('algorithm', 'unknown')
            success = turbo_data.get('success', False)
            pairs_processed = turbo_data.get('pairs_processed', 0)
            
            if algorithm not in algorithm_performance:
                algorithm_performance[algorithm] = {
                    'total': 0,
                    'successful': 0,
                    'success_rate': 0.0,
                    'avg_pairs': 0.0
                }
            
            algorithm_performance[algorithm]['total'] += 1
            if success:
                algorithm_performance[algorithm]['successful'] += 1
            total_pairs += pairs_processed
        
        # Calculer les taux de réussite par algorithme
        for algo_data in algorithm_performance.values():
            if algo_data['total'] > 0:
                algo_data['success_rate'] = algo_data['successful'] / algo_data['total']
        
        average_pairs_processed = total_pairs / total_turbos if total_turbos > 0 else 0.0
        
        # Performance récente (derniers 10 turbos)
        recent_entries = sorted(
            turbo_history.items(), 
            key=lambda x: x[1].get('timestamp', ''), 
            reverse=True
        )[:10]
        
        recent_performance = []
        for turbo_id, turbo_data in recent_entries:
            recent_performance.append({
                'turbo_id': turbo_id,
                'challenge_title': turbo_data.get('challenge_title', '')[:30],
                'success': turbo_data.get('success', False),
                'algorithm': turbo_data.get('algorithm', ''),
                'pairs_processed': turbo_data.get('pairs_processed', 0),
                'timestamp': turbo_data.get('timestamp', '')
            })
        
        response = TurboStatisticsResponse(
            profile_id=profile_id,
            total_turbos=total_turbos,
            successful_turbos=successful_turbos,
            failed_turbos=failed_turbos,
            success_rate=success_rate,
            average_pairs_processed=average_pairs_processed,
            algorithm_performance=algorithm_performance,
            recent_performance=recent_performance,
            trends={}  # À implémenter si nécessaire
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting turbo statistics for {profile_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get turbo statistics")


@router.get("/algorithms", response_model=AvailableAlgorithmsResponse)
async def get_available_algorithms():
    """
    Récupère la liste des algorithmes turbo disponibles
    Basé sur les algorithmes supportés dans gsui.py
    """
    try:
        algorithms = [
            {
                "name": "hybrid",
                "description": "Hybrid ensemble algorithm - combines multiple strategies"
            },
            {
                "name": "position_aware",
                "description": "Position-aware algorithm - considers photo ranking position"
            },
            {
                "name": "adaptive_time", 
                "description": "Time-adaptive algorithm - adjusts based on challenge time left"
            },
            {
                "name": "bruno_custom_refined",
                "description": "Bruno's custom refined algorithm - advanced heuristics"
            },
            {
                "name": "ratio_low",
                "description": "Ratio-low algorithm - prefers photos with lower ratios"
            },
            {
                "name": "votes_high",
                "description": "Votes-high algorithm - prefers photos with more votes"
            },
            {
                "name": "random",
                "description": "Random selection - for testing and comparison"
            }
        ]
        
        return AvailableAlgorithmsResponse(algorithms=algorithms)
        
    except Exception as e:
        logger.error(f"Error getting available algorithms: {e}")
        raise HTTPException(status_code=500, detail="Failed to get available algorithms")


@router.delete("/{profile_id}/turbo/cancel/{challenge_id}")
async def cancel_turbo(
    profile_id: str = Path(..., description="Profile ID"),
    challenge_id: str = Path(..., description="Challenge ID")
):
    """Annule l'exécution turbo en cours pour un challenge"""
    try:
        logger.info(f"🛑 Cancelling turbo for profile {profile_id}, challenge {challenge_id}")
        
        # Vérifier que le profil existe
        user = config_manager.get_user(profile_id)
        if not user:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        # Annuler l'exécution turbo
        cancelled = await turbo_executor.cancel_turbo_execution(profile_id, challenge_id)
        
        if not cancelled:
            raise HTTPException(status_code=404, detail="No active turbo found for this challenge")
        
        # Notifier via WebSocket
        await connection_manager.notify_turbo_cancelled(profile_id, challenge_id)
        
        logger.info(f"✅ Turbo cancelled for profile {profile_id}, challenge {challenge_id}")
        return {"message": "Turbo execution cancelled successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling turbo: {e}")
        raise HTTPException(status_code=500, detail="Failed to cancel turbo execution")


async def _save_turbo_status(profile_id: str, turbo_id: str, status_data: Dict[str, Any]):
    """Sauvegarde le statut turbo dans la configuration"""
    try:
        turbo_statuses = config_manager.get_user_section(profile_id, 'turbo_status') or {}
        challenge_id = status_data.get('challenge_id', '')
        turbo_status_key = f"{challenge_id}_current"
        
        turbo_statuses[turbo_status_key] = status_data
        config_manager.update_user_section(profile_id, 'turbo_status', turbo_statuses)
        
    except Exception as e:
        logger.error(f"Error saving turbo status: {e}")


async def _execute_turbo_background(
    profile_id: str,
    turbo_id: str,
    request: TurboExecutionRequest,
    algorithm: str,
    xtoken: str
):
    """Exécute le turbo en arrière-plan"""
    try:
        logger.info(f"🚀 Starting background turbo execution: {turbo_id}")
        
        # Déléguer l'exécution au service turbo_executor
        result = await turbo_executor.execute_turbo(
            profile_id=profile_id,
            turbo_id=turbo_id,
            challenge_id=request.challenge_id,
            challenge_title=request.challenge_title,
            challenge_time_left=request.challenge_time_left,
            algorithm=algorithm,
            xtoken=xtoken
        )
        
        logger.info(f"✅ Background turbo execution completed: {turbo_id}, success: {result.get('success', False)}")
        
    except Exception as e:
        logger.error(f"❌ Background turbo execution failed: {turbo_id}, error: {e}")
        
        # Mettre à jour le statut avec l'erreur
        error_status = {
            'turbo_id': turbo_id,
            'profile_id': profile_id,
            'challenge_id': request.challenge_id,
            'status': 'failed',
            'error_message': str(e),
            'execution_completed_at': datetime.now().isoformat()
        }
        
        #await _save_turbo_status(profile_id, turbo_id, error_status)
        await connection_manager.notify_turbo_failed(profile_id, turbo_id, str(e))