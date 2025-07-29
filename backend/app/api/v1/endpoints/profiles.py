"""
Profile API endpoints for mobile app registration and management
"""

from fastapi import APIRouter, HTTPException, Depends, Query, Path
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime
import re

from app.schemas.profile import (
    ProfileRegisterRequest,
    ProfileRegisterResponse,
    ProfileInfoResponse,
    ProfileListResponse,
    ProfileUpdateRequest,
    ProfileValidationRequest,
    ProfileValidationResponse,
    ProfileStatsResponse,
    ErrorResponse
)
from app.services.config_manager import config_manager
from app.services.gurushots_api import GuruShotsAPI
from app.websockets.connection_manager import connection_manager

logger = logging.getLogger(__name__)

router = APIRouter()


async def validate_gs_token(gs_token: str) -> tuple[bool, Optional[Dict], Optional[str]]:
    """Valide un gs_token en faisant un appel test à GuruShots"""
    try:
        # Créer une instance temporaire de l'API GuruShots
        api = GuruShotsAPI(token=gs_token)
        
        # Test simple : récupérer le profil utilisateur
        user_info = await api.get_user_profile()
        
        if user_info and user_info.get('success'):
            return True, user_info.get('data'), None
        else:
            return False, None, "Invalid token or API error"
            
    except Exception as e:
        logger.error(f"Error validating gs_token: {e}")
        return False, None, str(e)


@router.post("/register", response_model=ProfileRegisterResponse)
async def register_profile(request: ProfileRegisterRequest):
    """
    Enregistre ou connecte un profil pour l'app mobile
    
    - Si le profil existe et a un token : connexion simple
    - Si le profil existe sans token : met à jour avec gs_token fourni
    - Si nouveau profil : crée avec gs_token fourni
    """
    try:
        profile_name = request.profile_name
        gs_token = request.gs_token
        
        logger.info(f"📱 Registration request for profile: {profile_name}")
        
        # Vérifier si le profil existe déjà
        existing_user = config_manager.get_user(profile_name)
        
        if existing_user:
            # Profil existant
            existing_token = existing_user.get('xtoken', '')
            
            if existing_token and not gs_token:
                # Profil existe avec token, connexion simple
                logger.info(f"✅ Existing profile login: {profile_name}")
                
                return ProfileRegisterResponse(
                    profile_id=profile_name,
                    profile_name=profile_name,
                    status="existing",
                    message="Profile connected successfully",
                    has_valid_token=True,
                    created_at=existing_user.get('created_at'),
                    updated_at=existing_user.get('updated_at')
                )
                
            elif gs_token:
                # Mise à jour du token existant ou ajout de token manquant
                logger.info(f"🔄 Updating token for profile: {profile_name}")
                
                # Optionnel : Valider le nouveau token
                # is_valid, user_info, error = await validate_gs_token(gs_token)
                # if not is_valid:
                #     raise HTTPException(status_code=400, detail=f"Invalid gs_token: {error}")
                
                # Mettre à jour le profil
                update_success = config_manager.update_user(profile_name, {
                    'xtoken': gs_token,
                    'updated_at': datetime.now().isoformat()
                })
                
                if not update_success:
                    raise HTTPException(status_code=500, detail="Failed to update profile")
                
                return ProfileRegisterResponse(
                    profile_id=profile_name,
                    profile_name=profile_name,
                    status="updated",
                    message="Profile token updated successfully",
                    has_valid_token=True,
                    updated_at=datetime.now()
                )
                
            else:
                # Profil existe mais pas de token fourni et pas de token existant
                raise HTTPException(
                    status_code=400, 
                    detail="Profile exists but has no token. Please provide gs_token."
                )
        
        else:
            # Nouveau profil
            if not gs_token:
                raise HTTPException(
                    status_code=400,
                    detail="New profile requires gs_token"
                )
            
            logger.info(f"🆕 Creating new profile: {profile_name}")
            
            # Optionnel : Valider le token
            # is_valid, user_info, error = await validate_gs_token(gs_token)
            # if not is_valid:
            #     raise HTTPException(status_code=400, detail=f"Invalid gs_token: {error}")
            
            # Créer le nouveau profil avec les valeurs par défaut de gsui.py
            user_data = {
                'user_name': profile_name,
                'xtoken': gs_token,
                'turbo_algorithm': '[hybrid,position_aware,adaptive_time]',  # Défaut optimal
                'auto_optimize_turbo': False,
                'turbo_history_enabled': True,
                'created_at': datetime.now().isoformat()
            }
            
            create_success = config_manager.create_user(profile_name, user_data)
            
            if not create_success:
                raise HTTPException(status_code=500, detail="Failed to create profile")
            
            return ProfileRegisterResponse(
                profile_id=profile_name,
                profile_name=profile_name,
                status="created",
                message="Profile created successfully",
                has_valid_token=True,
                created_at=datetime.now()
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error registering profile {request.profile_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")


@router.get("/{profile_id}", response_model=ProfileInfoResponse)
async def get_profile_info(
    profile_id: str = Path(..., description="Profile ID")
):
    """Récupère les informations détaillées d'un profil"""
    try:
        user = config_manager.get_user(profile_id)
        
        if not user:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        # Calculer les statistiques
        challenges = config_manager.get_user_challenges(profile_id)
        strategies_count = len(challenges)
        
        # Compter les stratégies actives (à implémenter selon la logique)
        active_strategies = sum(1 for c in challenges.values() 
                              if c.get('status') in ['pending', 'running'])
        
        # Historique turbo
        turbo_history = config_manager.get_turbo_history(profile_id)
        turbos_count = len(turbo_history)
        
        return ProfileInfoResponse(
            profile_id=profile_id,
            profile_name=user.get('user_name', profile_id),
            has_valid_token=bool(user.get('xtoken')),
            turbo_algorithm=user.get('turbo_algorithm', 'hybrid'),
            auto_optimize_turbo=user.get('auto_optimize_turbo', False),
            turbo_history_enabled=user.get('turbo_history_enabled', True),
            created_at=user.get('created_at'),
            updated_at=user.get('updated_at'),
            total_strategies=strategies_count,
            active_strategies=active_strategies,
            total_turbos=turbos_count
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting profile info for {profile_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get profile info")


@router.get("/", response_model=ProfileListResponse)
async def list_profiles():
    """Liste tous les profils disponibles"""
    try:
        user_ids = config_manager.list_users()
        profiles = []
        
        for user_id in user_ids:
            try:
                user = config_manager.get_user(user_id)
                if user:
                    # Statistiques basiques
                    challenges = config_manager.get_user_challenges(user_id)
                    turbo_history = config_manager.get_turbo_history(user_id)
                    
                    profile_info = ProfileInfoResponse(
                        profile_id=user_id,
                        profile_name=user.get('user_name', user_id),
                        has_valid_token=bool(user.get('xtoken')),
                        turbo_algorithm=user.get('turbo_algorithm', 'hybrid'),
                        auto_optimize_turbo=user.get('auto_optimize_turbo', False),
                        turbo_history_enabled=user.get('turbo_history_enabled', True),
                        created_at=user.get('created_at'),
                        updated_at=user.get('updated_at'),
                        total_strategies=len(challenges),
                        active_strategies=0,  # À calculer selon la logique
                        total_turbos=len(turbo_history)
                    )
                    profiles.append(profile_info)
                    
            except Exception as e:
                logger.warning(f"Error processing profile {user_id}: {e}")
                continue
        
        return ProfileListResponse(
            profiles=profiles,
            total_count=len(profiles)
        )
        
    except Exception as e:
        logger.error(f"Error listing profiles: {e}")
        raise HTTPException(status_code=500, detail="Failed to list profiles")


@router.put("/{profile_id}", response_model=ProfileInfoResponse)
async def update_profile(
    profile_id: str = Path(..., description="Profile ID"),
    updates: ProfileUpdateRequest = ...
):
    """Met à jour les paramètres d'un profil"""
    try:
        # Vérifier que le profil existe
        user = config_manager.get_user(profile_id)
        if not user:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        # Préparer les mises à jour
        update_data = {}
        
        if updates.turbo_algorithm is not None:
            update_data['turbo_algorithm'] = updates.turbo_algorithm
            
        if updates.auto_optimize_turbo is not None:
            update_data['auto_optimize_turbo'] = updates.auto_optimize_turbo
            
        if updates.turbo_history_enabled is not None:
            update_data['turbo_history_enabled'] = updates.turbo_history_enabled
            
        if updates.gs_token is not None:
            # Optionnel : Valider le nouveau token
            update_data['xtoken'] = updates.gs_token
        
        if update_data:
            update_data['updated_at'] = datetime.now().isoformat()
            success = config_manager.update_user(profile_id, update_data)
            
            if not success:
                raise HTTPException(status_code=500, detail="Failed to update profile")
        
        # Retourner les informations mises à jour
        return await get_profile_info(profile_id)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating profile {profile_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update profile")


@router.post("/validate-token", response_model=ProfileValidationResponse)
async def validate_token(request: ProfileValidationRequest):
    """Valide un gs_token GuruShots"""
    try:
        is_valid, user_info, error_message = await validate_gs_token(request.gs_token)
        
        return ProfileValidationResponse(
            is_valid=is_valid,
            user_info=user_info,
            error_message=error_message,
            validation_timestamp=datetime.now()
        )
        
    except Exception as e:
        logger.error(f"Error validating token: {e}")
        return ProfileValidationResponse(
            is_valid=False,
            user_info=None,
            error_message=str(e),
            validation_timestamp=datetime.now()
        )


@router.get("/{profile_id}/stats", response_model=ProfileStatsResponse)
async def get_profile_stats(
    profile_id: str = Path(..., description="Profile ID")
):
    """Récupère les statistiques détaillées d'un profil"""
    try:
        user = config_manager.get_user(profile_id)
        if not user:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        # Statistiques des stratégies
        challenges = config_manager.get_user_challenges(profile_id)
        strategy_stats = {}
        
        for challenge in challenges.values():
            status = challenge.get('status', 'unknown')
            strategy_stats[status] = strategy_stats.get(status, 0) + 1
        
        # Statistiques des turbos
        turbo_history = config_manager.get_turbo_history(profile_id)
        turbo_stats = {
            'total': len(turbo_history),
            'success': sum(1 for t in turbo_history if t.get('success', False)),
            'failed': sum(1 for t in turbo_history if not t.get('success', True))
        }
        
        # Performance
        performance = {}
        if turbo_stats['total'] > 0:
            performance['success_rate'] = turbo_stats['success'] / turbo_stats['total']
        
        return ProfileStatsResponse(
            profile_id=profile_id,
            strategies=strategy_stats,
            turbos=turbo_stats,
            performance=performance
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting profile stats for {profile_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get profile stats")


@router.delete("/{profile_id}")
async def delete_profile(
    profile_id: str = Path(..., description="Profile ID"),
    confirm: bool = Query(False, description="Confirmation required")
):
    """Supprime un profil (avec confirmation)"""
    if not confirm:
        raise HTTPException(
            status_code=400,
            detail="Profile deletion requires confirmation. Add ?confirm=true"
        )
    
    try:
        user = config_manager.get_user(profile_id)
        if not user:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        # TODO: Implémenter la suppression dans ConfigManager
        # Pour l'instant, on refuse la suppression
        raise HTTPException(
            status_code=501,
            detail="Profile deletion not implemented yet"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting profile {profile_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete profile")