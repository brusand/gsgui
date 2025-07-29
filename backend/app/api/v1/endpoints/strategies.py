"""
Scheduled Strategies API endpoints - Migration from gsui.py
"""

from fastapi import APIRouter, HTTPException, Depends, Query, Path
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime
import uuid

from app.schemas.strategy import (
    ScheduleStrategyRequest,
    ScheduledStrategyResponse,
    StrategyListResponse,
    StrategyUpdateRequest,
    AvailableStrategiesResponse,
    StrategyExecutionResult,
    StrategyStatusUpdate
)
from app.services.config_manager import config_manager
from app.services.strategy_scheduler import strategy_scheduler
from app.websockets.connection_manager import connection_manager
from app.websockets.turbo_notifications import *

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/{profile_id}/strategies", response_model=ScheduledStrategyResponse)
async def schedule_strategy(
    profile_id: str = Path(..., description="Profile ID"),
    request: ScheduleStrategyRequest = ...
):
    """
    Programme une stratégie pour un challenge
    Équivalent de save_scheduled_strategy() dans gsui.py
    """
    try:
        logger.info(f"📅 Scheduling strategy {request.strategy_name} for profile {profile_id}, challenge {request.challenge_id}")
        
        # Vérifier que le profil existe
        user = config_manager.get_user(profile_id)
        if not user:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        # Générer un ID unique pour la stratégie
        strategy_id = f"{request.challenge_id}_{int(datetime.now().timestamp())}"
        
        # Préparer les données de la stratégie
        strategy_data = {
            'strategy_id': strategy_id,
            'challenge_id': request.challenge_id,
            'strategy_name': request.strategy_name,
            'challenge_title': request.challenge_title or f"Challenge {request.challenge_id}",
            'scheduled_at': request.scheduled_at.isoformat(),
            'status': 'pending',
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        # Sauvegarder dans la section scheduled_strategies du .ini
        scheduled_strategies = config_manager.get_user_section(profile_id, 'scheduled_strategies') or {}
        scheduled_strategies[strategy_id] = strategy_data
        
        success = config_manager.update_user_section(profile_id, 'scheduled_strategies', scheduled_strategies)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to save scheduled strategy")
        
        # Programmer l'exécution avec APScheduler
        await strategy_scheduler.schedule_strategy(
            profile_id=profile_id,
            strategy_id=strategy_id,
            strategy_data=strategy_data
        )
        
        response = ScheduledStrategyResponse(
            strategy_id=strategy_id,
            profile_id=profile_id,
            challenge_id=request.challenge_id,
            strategy_name=request.strategy_name,
            challenge_title=request.challenge_title,
            scheduled_at=request.scheduled_at,
            status='pending',
            created_at=datetime.now()
        )
        
        # Notifier via WebSocket
        await connection_manager.notify_strategy_scheduled(profile_id, response.dict())
        
        logger.info(f"✅ Strategy scheduled successfully: {strategy_id}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error scheduling strategy: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to schedule strategy: {str(e)}")


@router.get("/{profile_id}/strategies", response_model=StrategyListResponse)
async def list_strategies(
    profile_id: str = Path(..., description="Profile ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(100, ge=1, le=500)
):
    """
    Liste les stratégies programmées pour un profil
    Équivalent de load_and_restore_scheduled_strategies() dans gsui.py
    """
    try:
        logger.info(f"📋 Listing strategies for profile {profile_id}")
        
        # Vérifier que le profil existe
        user = config_manager.get_user(profile_id)
        if not user:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        # Récupérer les stratégies programmées
        scheduled_strategies = config_manager.get_user_section(profile_id, 'scheduled_strategies') or {}
        
        strategies = []
        pending_count = 0
        running_count = 0
        
        for strategy_id, strategy_data in scheduled_strategies.items():
            try:
                # Filtrer par statut si demandé
                if status and strategy_data.get('status') != status:
                    continue
                
                # Compter les statuts
                strategy_status = strategy_data.get('status', 'pending')
                if strategy_status == 'pending':
                    pending_count += 1
                elif strategy_status == 'running':
                    running_count += 1
                
                strategy_response = ScheduledStrategyResponse(
                    strategy_id=strategy_id,
                    profile_id=profile_id,
                    challenge_id=strategy_data.get('challenge_id', ''),
                    strategy_name=strategy_data.get('strategy_name', ''),
                    challenge_title=strategy_data.get('challenge_title'),
                    scheduled_at=datetime.fromisoformat(strategy_data.get('scheduled_at', datetime.now().isoformat())),
                    status=strategy_status,
                    created_at=datetime.fromisoformat(strategy_data.get('created_at', datetime.now().isoformat())),
                    updated_at=datetime.fromisoformat(strategy_data.get('updated_at', datetime.now().isoformat())) if strategy_data.get('updated_at') else None
                )
                strategies.append(strategy_response)
                
            except Exception as e:
                logger.warning(f"Error processing strategy {strategy_id}: {e}")
                continue
        
        # Trier par date de programmation
        strategies.sort(key=lambda x: x.scheduled_at)
        
        # Limiter les résultats
        if len(strategies) > limit:
            strategies = strategies[:limit]
        
        response = StrategyListResponse(
            strategies=strategies,
            total_count=len(strategies),
            pending_count=pending_count,
            running_count=running_count
        )
        
        logger.info(f"✅ Listed {len(strategies)} strategies for profile {profile_id}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing strategies for {profile_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to list strategies")


@router.get("/{profile_id}/strategies/{strategy_id}", response_model=ScheduledStrategyResponse)
async def get_strategy(
    profile_id: str = Path(..., description="Profile ID"),
    strategy_id: str = Path(..., description="Strategy ID")
):
    """Récupère les détails d'une stratégie spécifique"""
    try:
        # Vérifier que le profil existe
        user = config_manager.get_user(profile_id)
        if not user:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        # Récupérer la stratégie
        scheduled_strategies = config_manager.get_user_section(profile_id, 'scheduled_strategies') or {}
        strategy_data = scheduled_strategies.get(strategy_id)
        
        if not strategy_data:
            raise HTTPException(status_code=404, detail="Strategy not found")
        
        response = ScheduledStrategyResponse(
            strategy_id=strategy_id,
            profile_id=profile_id,
            challenge_id=strategy_data.get('challenge_id', ''),
            strategy_name=strategy_data.get('strategy_name', ''),
            challenge_title=strategy_data.get('challenge_title'),
            scheduled_at=datetime.fromisoformat(strategy_data.get('scheduled_at', datetime.now().isoformat())),
            status=strategy_data.get('status', 'pending'),
            created_at=datetime.fromisoformat(strategy_data.get('created_at', datetime.now().isoformat())),
            updated_at=datetime.fromisoformat(strategy_data.get('updated_at', datetime.now().isoformat())) if strategy_data.get('updated_at') else None
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting strategy {strategy_id} for profile {profile_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get strategy")


@router.put("/{profile_id}/strategies/{strategy_id}", response_model=ScheduledStrategyResponse)
async def update_strategy(
    profile_id: str = Path(..., description="Profile ID"),
    strategy_id: str = Path(..., description="Strategy ID"),
    updates: StrategyUpdateRequest = ...
):
    """
    Met à jour une stratégie programmée
    """
    try:
        logger.info(f"🔄 Updating strategy {strategy_id} for profile {profile_id}")
        
        # Vérifier que le profil existe
        user = config_manager.get_user(profile_id)
        if not user:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        # Récupérer les stratégies
        scheduled_strategies = config_manager.get_user_section(profile_id, 'scheduled_strategies') or {}
        strategy_data = scheduled_strategies.get(strategy_id)
        
        if not strategy_data:
            raise HTTPException(status_code=404, detail="Strategy not found")
        
        # Préparer les mises à jour
        old_status = strategy_data.get('status', 'pending')
        update_data = {}
        
        if updates.strategy_name is not None:
            update_data['strategy_name'] = updates.strategy_name
            
        if updates.scheduled_at is not None:
            update_data['scheduled_at'] = updates.scheduled_at.isoformat()
            # Re-programmer avec APScheduler
            await strategy_scheduler.reschedule_strategy(
                profile_id=profile_id,
                strategy_id=strategy_id,
                new_schedule_time=updates.scheduled_at
            )
            
        if updates.status is not None:
            update_data['status'] = updates.status
            if updates.status == 'cancelled':
                # Annuler dans APScheduler
                await strategy_scheduler.cancel_strategy(profile_id, strategy_id)
        
        if update_data:
            update_data['updated_at'] = datetime.now().isoformat()
            strategy_data.update(update_data)
            scheduled_strategies[strategy_id] = strategy_data
            
            success = config_manager.update_user_section(profile_id, 'scheduled_strategies', scheduled_strategies)
            
            if not success:
                raise HTTPException(status_code=500, detail="Failed to update strategy")
        
        # Retourner la stratégie mise à jour
        response = ScheduledStrategyResponse(
            strategy_id=strategy_id,
            profile_id=profile_id,
            challenge_id=strategy_data.get('challenge_id', ''),
            strategy_name=strategy_data.get('strategy_name', ''),
            challenge_title=strategy_data.get('challenge_title'),
            scheduled_at=datetime.fromisoformat(strategy_data.get('scheduled_at', datetime.now().isoformat())),
            status=strategy_data.get('status', 'pending'),
            created_at=datetime.fromisoformat(strategy_data.get('created_at', datetime.now().isoformat())),
            updated_at=datetime.now()
        )
        
        # Notifier via WebSocket si le statut a changé
        new_status = strategy_data.get('status', 'pending')
        if old_status != new_status:
            await connection_manager.notify_strategy_status_changed(
                profile_id, strategy_id, old_status, new_status
            )
        
        logger.info(f"✅ Strategy {strategy_id} updated successfully")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating strategy {strategy_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update strategy")


@router.delete("/{profile_id}/strategies/{strategy_id}")
async def delete_strategy(
    profile_id: str = Path(..., description="Profile ID"),
    strategy_id: str = Path(..., description="Strategy ID")
):
    """
    Supprime une stratégie programmée
    Équivalent de remove_scheduled_strategy() dans gsui.py
    """
    try:
        logger.info(f"🗑️ Deleting strategy {strategy_id} for profile {profile_id}")
        
        # Vérifier que le profil existe
        user = config_manager.get_user(profile_id)
        if not user:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        # Récupérer les stratégies
        scheduled_strategies = config_manager.get_user_section(profile_id, 'scheduled_strategies') or {}
        
        if strategy_id not in scheduled_strategies:
            raise HTTPException(status_code=404, detail="Strategy not found")
        
        # Annuler la tâche programmée
        await strategy_scheduler.cancel_strategy(profile_id, strategy_id)
        
        # Supprimer de la configuration
        del scheduled_strategies[strategy_id]
        success = config_manager.update_user_section(profile_id, 'scheduled_strategies', scheduled_strategies)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete strategy")
        
        # Notifier via WebSocket
        await connection_manager.notify_strategy_deleted(profile_id, strategy_id)
        
        logger.info(f"✅ Strategy {strategy_id} deleted successfully")
        return {"message": "Strategy deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting strategy {strategy_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete strategy")


@router.get("/available", response_model=AvailableStrategiesResponse)
async def get_available_strategies():
    """
    Récupère la liste des stratégies disponibles
    Basé sur les stratégies supportées dans gsui.py
    """
    try:
        strategies = [
            {
                "name": "4m",
                "description": "Vote every 4 minutes until end",
                "min_duration_minutes": 5
            },
            {
                "name": "fill",
                "description": "Fill remaining votes immediately",
                "min_duration_minutes": 0
            },
            {
                "name": "boost",
                "description": "Boost votes at optimal times",
                "min_duration_minutes": 10
            },
            {
                "name": "swap",
                "description": "Swap votes strategically",
                "min_duration_minutes": 15
            }
        ]
        
        return AvailableStrategiesResponse(strategies=strategies)
        
    except Exception as e:
        logger.error(f"Error getting available strategies: {e}")
        raise HTTPException(status_code=500, detail="Failed to get available strategies")