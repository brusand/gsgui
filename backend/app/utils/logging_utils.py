"""
Logging utilities for GSGUI Backend
Provides enhanced logging with challenge titles and consistent formatting
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any
from functools import lru_cache

# Cache pour les titres de challenges pour éviter les appels API répétés
_challenge_titles_cache: Dict[str, str] = {}

def setup_logger(name: str) -> logging.Logger:
    """Setup a logger with consistent formatting"""
    logger = logging.getLogger(name)
    
    # Si le logger n'a pas de handlers, utiliser la config par défaut
    if not logger.handlers:
        # Utiliser le logger racine configuré dans main.py
        logger.setLevel(logging.INFO)
    
    return logger

def update_challenge_titles_cache(challenges_data: Dict[str, Any]):
    """
    Met à jour le cache des titres de challenges
    
    Args:
        challenges_data: Données des challenges de l'API (format: {id: {title: ...}})
    """
    global _challenge_titles_cache
    
    for challenge_id, challenge_info in challenges_data.items():
        if isinstance(challenge_info, dict) and 'title' in challenge_info:
            _challenge_titles_cache[str(challenge_id)] = challenge_info['title']

def get_challenge_title(challenge_id: str) -> str:
    """
    Récupère le titre d'un challenge depuis le cache
    
    Args:
        challenge_id: ID du challenge
        
    Returns:
        Titre du challenge ou l'ID si non trouvé
    """
    return _challenge_titles_cache.get(str(challenge_id), f"Challenge {challenge_id}")

def log_with_profile(
    logger: logging.Logger,
    level: str,
    message: str,
    profile_id: Optional[str] = None,
    challenge_id: Optional[str] = None,
    **kwargs
):
    """
    Log universel avec profile ID en premier et titre de challenge
    
    Args:
        logger: Logger à utiliser
        level: Niveau de log (info, warning, error, etc.)
        message: Message de base
        profile_id: ID du profil (TOUJOURS en premier si fourni)
        challenge_id: ID du challenge (enrichi avec titre)
        **kwargs: Paramètres supplémentaires
    """
    # Construire le message enrichi
    enhanced_message = message
    
    # Remplacer les IDs de challenges par leurs titres
    if challenge_id:
        challenge_title = get_challenge_title(challenge_id)
        # Remplacements possibles
        replacements = [
            (f"challenge {challenge_id}", f'"{challenge_title}" ({challenge_id})'),
            (f"Challenge {challenge_id}", f'"{challenge_title}" ({challenge_id})'),
            (f"challenge_id {challenge_id}", f'"{challenge_title}" ({challenge_id})'),
            (challenge_id, f'"{challenge_title}" ({challenge_id})')
        ]
        
        for old, new in replacements:
            if old in enhanced_message:
                enhanced_message = enhanced_message.replace(old, new)
                break
    
    # Ajouter des paramètres supplémentaires si fournis
    if kwargs:
        extra_info = " | ".join([f"{k}={v}" for k, v in kwargs.items()])
        enhanced_message = f"{enhanced_message} | {extra_info}"
    
    # TOUJOURS ajouter le profile ID en PREMIER si fourni
    if profile_id:
        enhanced_message = f"[{profile_id}] {enhanced_message}"
    
    # Logger selon le niveau
    log_func = getattr(logger, level.lower(), logger.info)
    log_func(enhanced_message)

def log_challenge_action(
    logger: logging.Logger, 
    level: str, 
    message: str, 
    challenge_id: Optional[str] = None,
    profile_id: Optional[str] = None,
    **kwargs
):
    """
    DEPRECATED: Use log_with_profile instead
    Log une action liée à un challenge avec titre enrichi
    """
    log_with_profile(logger, level, message, profile_id, challenge_id, **kwargs)

def log_strategy_execution(
    logger: logging.Logger,
    challenge_id: str,
    strategy_name: str,
    action: str,
    profile_id: str,
    status: str = "started",
    **kwargs
):
    """
    Log spécialisé pour l'exécution de stratégies
    
    Args:
        logger: Logger à utiliser
        challenge_id: ID du challenge
        strategy_name: Nom de la stratégie
        action: Type d'action (vote, submit, swap, etc.)
        profile_id: ID du profil
        status: Statut (started, completed, failed, etc.)
        **kwargs: Paramètres supplémentaires
    """
    challenge_title = get_challenge_title(challenge_id)
    
    status_emoji = {
        "started": "🎯",
        "completed": "✅", 
        "failed": "❌",
        "scheduled": "📅",
        "executing": "⚡"
    }.get(status, "📋")
    
    message = f'{status_emoji} Strategy "{strategy_name}" {action} {status} for "{challenge_title}" ({challenge_id})'
    
    if kwargs:
        extra_info = " | ".join([f"{k}={v}" for k, v in kwargs.items()])
        message = f"{message} | {extra_info}"
    
    logger.info(f"[{profile_id}] {message}")

def log_api_call(
    logger: logging.Logger,
    endpoint: str,
    challenge_id: Optional[str] = None,
    profile_id: Optional[str] = None,
    status: str = "called",
    response_data: Optional[Dict] = None
):
    """
    Log spécialisé pour les appels API
    
    Args:
        logger: Logger à utiliser  
        endpoint: Endpoint appelé
        challenge_id: ID du challenge (optionnel)
        profile_id: ID du profil (optionnel)
        status: Statut de l'appel
        response_data: Données de réponse (optionnel)
    """
    status_emoji = {
        "called": "📡",
        "success": "✅",
        "failed": "❌",
        "timeout": "⏰"
    }.get(status, "📋")
    
    message = f"{status_emoji} API {endpoint} {status}"
    
    if challenge_id:
        challenge_title = get_challenge_title(challenge_id)
        message = f'{message} for "{challenge_title}" ({challenge_id})'
    
    if profile_id:
        message = f"[{profile_id}] {message}"
    
    if response_data and isinstance(response_data, dict):
        if "status" in response_data:
            message = f"{message} | HTTP {response_data['status']}"
        if "count" in response_data:
            message = f"{message} | {response_data['count']} items"
    
    logger.info(message)