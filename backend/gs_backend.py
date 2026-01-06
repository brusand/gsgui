#!/usr/bin/env python3
"""
Backend API avec vrais challenges GuruShots
"""

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import uvicorn
import asyncio
import aiohttp
import ssl
from configobj import ConfigObj
import threading
import os
import json
from typing import Set
import sys
import logging
from app.websockets.connection_manager import connection_manager
from app.utils.logging_utils import setup_logger, log_with_profile, log_strategy_execution, log_api_call, update_challenge_titles_cache

# Setup du logger principal
logger = setup_logger("gs_backend")

# Configuration des chemins relatifs au projet (backend est un sous-dossier)
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)
GSGUI_INI_PATH = os.path.join(PROJECT_ROOT, 'data', 'gsgui.ini')

# Imports locaux maintenant que le fichier est dans backend/
try:
    from app.services.gurushots_api import GuruShotsAPI
    REAL_VOTE_AVAILABLE = True
    logger.info("✅ GuruShotsAPI imported successfully")
except ImportError as e:
    logger.warning(f"⚠️ GuruShotsAPI import failed: {e}")
    REAL_VOTE_AVAILABLE = False

try:
    from app.services.strategy_scheduler import StrategyScheduler
    STRATEGY_SCHEDULER_AVAILABLE = True
    logger.info("✅ StrategyScheduler imported successfully")
except ImportError as e:
    logger.warning(f"⚠️ Strategy Scheduler service not available: {e}")
    STRATEGY_SCHEDULER_AVAILABLE = False

# Helper function pour créer GuruShotsAPI
def create_gurushots_api(token):
    """Crée une instance GuruShotsAPI"""
    try:
        return GuruShotsAPI(token)
    except Exception as e:
        logger.warning(f"⚠️ Error creating GuruShotsAPI: {e}")
        return None

app = FastAPI(title="GSGUI Real API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration SSL
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

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
    challenge_ids: List[str]  # Support multiple challenges like fill
    challenge_id: Optional[str] = None  # Keep for backward compatibility
    challenge_title: Optional[str] = None
    challenge_time_left: Optional[str] = None
    algorithm: Optional[str] = None

class SimpleVoteRequest(BaseModel):
    challenge_url: str
    vote_count: int

class FillRequest(BaseModel):
    challenge_ids: List[str]
    votes_per_challenge: int

class MultiVoteRequest(BaseModel):
    challenge_ids: List[str]
    votes_per_challenge: int

# In-memory storage
profiles = {}
strategies = {}
turbo_executions = {}

# Instances des services
gurushots_api = None
strategy_scheduler = None

# Configuration files with thread locks
gsgui_ini_lock = threading.Lock()
strategies_ini_lock = threading.Lock()
backend_config_lock = threading.Lock()
BACKEND_STRATEGIES_FILE = os.path.join(os.path.dirname(__file__), "data", "backend_strategies.ini")
BACKEND_TURBO_FILE = "backend_turbo.ini"

# WebSocket connections for real-time logs
websocket_connections: Set[WebSocket] = set()

# Challenges et stratégies en mémoire
challenges = {}
strategies = {}
profiles = {}  # Profils en mémoire

# Services
class ProfileService:
    """Service pour gérer les profils depuis gsgui.ini"""
    
    @staticmethod
    def get_profile(profile_id: str) -> Optional[dict]:
        """Récupère un profil par son ID depuis gsgui.ini"""
        try:
            with gsgui_ini_lock:
                config = ConfigObj(GSGUI_INI_PATH, encoding='utf-8')
                
                if 'players' not in config:
                    return None
                
                if profile_id not in config['players']:
                    return None
                
                profile_data = config['players'][profile_id]
                return {
                    'profile_id': profile_id,
                    'xtoken': profile_data.get('xtoken', ''),
                    'turbo_algorithm': profile_data.get('turbo_algorithm', ''),
                    'auto_optimize_turbo': profile_data.get('auto_optimize_turbo', False)
                }
        except Exception as e:
            print(f"❌ Error getting profile {profile_id}: {e}")
            return None
    
    @staticmethod
    def get_all_profiles() -> dict:
        """Récupère tous les profils depuis gsgui.ini"""
        try:
            with gsgui_ini_lock:
                config = ConfigObj(GSGUI_INI_PATH, encoding='utf-8')
                
                profiles_dict = {}
                if 'players' in config:
                    for profile_id, profile_data in config['players'].items():
                        profiles_dict[profile_id] = {
                            'profile_id': profile_id,
                            'xtoken': profile_data.get('xtoken', ''),
                            'turbo_algorithm': profile_data.get('turbo_algorithm', ''),
                            'auto_optimize_turbo': profile_data.get('auto_optimize_turbo', False)
                        }
                
                return profiles_dict
        except Exception as e:
            print(f"❌ Error getting all profiles: {e}")
            return {}

class ChallengeService:
    """Service pour gérer les challenges"""
    
    @staticmethod
    async def get_challenge_data(challenge_id: str, profile_id: str) -> Optional[dict]:
        """Récupère les données d'un challenge via l'API GuruShots"""
        try:
            profile = ProfileService.get_profile(profile_id)
            if not profile or not profile['xtoken']:
                print(f"❌ No valid token for profile {profile_id}")
                return None
            
            real_challenges = await fetch_real_challenges(profile['xtoken'], profile_id)
            if not real_challenges:
                return None
                
            for challenge in real_challenges:
                if str(challenge.get('id')) == str(challenge_id):
                    return challenge
            
            print(f"⚠️ Challenge {challenge_id} not found in API response")
            return None
            
        except Exception as e:
            print(f"❌ Error getting challenge data for {challenge_id}: {e}")
            return None

# Cache pour les titres de challenges (éviter refetch constant)
challenge_titles_cache = {}
cache_last_update = None

async def get_challenge_title(challenge_id, profile_name=None):
    """Récupère le titre d'un challenge avec cache"""
    global challenge_titles_cache, cache_last_update
    
    # Vérifier cache (5 minutes de validité)
    now = datetime.now()
    if cache_last_update and (now - cache_last_update).seconds < 300:
        title = challenge_titles_cache.get(challenge_id)
        if title:
            return title
    
    # Refresh cache si nécessaire
    if profile_name:
        try:
            profile_id = profile_name.lower()
            if profile_id in profiles:
                x_token = profiles[profile_id].get('xtoken')
                if x_token:
                    real_challenges = await fetch_real_challenges(x_token, profile_id)
                    challenge_titles_cache = {ch['id']: ch['title'] for ch in real_challenges}
                    cache_last_update = now
                    return challenge_titles_cache.get(challenge_id, f"Challenge {challenge_id}")
        except Exception as e:
            print(f"⚠️ Error fetching challenge title: {e}")
    
    return f"Challenge {challenge_id}"

async def broadcast_log(message: str, log_type: str = "info", profile_name: str = None):
    """Diffuse un message de log à toutes les connexions WebSocket avec amélioration des titres"""
    if not websocket_connections:
        return
    
    # Améliorer le message si il contient un ID de challenge
    improved_message = message
    if "Challenge " in message and profile_name:
        try:
            import re
            # Chercher les patterns "Challenge XXXXX"
            challenge_ids = re.findall(r'Challenge (\d+)', message)
            for challenge_id in challenge_ids:
                title = await get_challenge_title(challenge_id, profile_name)
                improved_message = improved_message.replace(f"Challenge {challenge_id}", title)
        except Exception as e:
            print(f"⚠️ Error improving log message: {e}")
    
    log_data = {
        "timestamp": datetime.now().isoformat(),
        "type": log_type,
        "message": improved_message,
        "profile_id": profile_name
    }
    
    # Envoyer à toutes les connexions actives
    disconnected = set()
    for websocket in websocket_connections.copy():
        try:
            await websocket.send_text(json.dumps(log_data))
        except Exception:
            disconnected.add(websocket)
    
    # Nettoyer les connexions fermées
    websocket_connections.difference_update(disconnected)

def log_and_broadcast(message: str, log_type: str = "info", profile_name: str = None):
    """Log local + diffusion WebSocket (version synchrone) avec horodatage et profile_id"""
    from datetime import datetime
    
    # Ajouter horodatage et profile_id au message
    timestamp = datetime.now().strftime("%H:%M:%S")
    if profile_name:
        formatted_message = f"[{timestamp}] [{profile_name}] {message}"
    else:
        formatted_message = f"[{timestamp}] {message}"
    
    print(formatted_message)
    # Créer une tâche asynchrone pour la diffusion
    try:
        # Diffuser aux WebSockets par profil
        if profile_name:
            asyncio.create_task(connection_manager.notify_broadcast_log(
                profile_name, log_type, formatted_message))
        asyncio.create_task(broadcast_log(formatted_message, log_type, profile_name))
    except RuntimeError:
        # Si pas de loop actif, ignorer la diffusion
        pass

def get_aio_headers(xtoken: str) -> Dict[str, str]:
    """Retourne les headers pour l'API GuruShots"""
    return {
        'User-Agent': 'Mozilla/5.0 (X11; Linux i686; rv:39.0) Gecko/20100101 Firefox/39.0',
        'x-api-version': '8',
        'x-env': 'WEB',
        'X-requested-with': 'XMLHttpRequest',
        'X-token': xtoken
    }

async def fetch_real_challenges(xtoken: str, profile_id: str = None) -> List[Dict[str, Any]]:
    """Récupère les vrais challenges depuis l'API GuruShots"""
    try:
        headers = get_aio_headers(xtoken)
        log_api_call(logger, "get_my_active_challenges", status="called", profile_id=profile_id)
        
        connector = aiohttp.TCPConnector(ssl=False)
        async with aiohttp.ClientSession(headers=headers, connector=connector) as session:
            async with session.post('https://api.gurushots.com/rest/get_my_active_challenges') as response:
                log_api_call(logger, "get_my_active_challenges", status="success", response_data={"status": response.status}, profile_id=profile_id)
                
                if response.status != 200:
                    log_api_call(logger, "get_my_active_challenges", status="failed", response_data={"status": response.status}, profile_id=profile_id)
                    return []
                
                data = await response.json()
                log_api_call(logger, "get_my_active_challenges", status="success", response_data={
                    "status": response.status,
                    "keys": list(data.keys()) if isinstance(data, dict) else "Not a dict"
                }, profile_id=profile_id)
                
                # Debug : si success=false, afficher l'erreur
                if isinstance(data, dict) and not data.get('success', True):
                    error_code = data.get('error_code', 'unknown')
                    error_msg = data.get('error', 'No error message')
                    logger.error(f"❌ GuruShots API Error: {error_code} - {error_msg}")
                    logger.debug(f"🔍 Full response: {data}")
                
                challenges = []
                challenges_cache = {}  # Pour le cache des titres
                
                for challenge_data in data.get('challenges', []):
                    try:
                        # Mettre à jour le cache des titres
                        challenge_id = challenge_data.get('id')
                        challenge_title = challenge_data.get('title', f'Challenge {challenge_id}')
                        if challenge_id:
                            challenges_cache[str(challenge_id)] = challenge_title
                        
                        timeleft = challenge_data['time_left']
                        
                        # Calculer end_time comme dans gs_backend_ui.py
                        from datetime import datetime, timedelta
                        days = timeleft.get('days', 0)
                        hours = timeleft.get('hours', 0)
                        minutes = timeleft.get('minutes', 0)
                        seconds = timeleft.get('seconds', 0)
                        
                        # Calcul du temps total en secondes pour tri et countdown (comme gs_backend_ui.py)
                        time_left_seconds = days * 86400 + hours * 3600 + minutes * 60 + seconds
                        
                        # Calculer la date de fin
                        end_datetime = datetime.now() + timedelta(seconds=time_left_seconds)
                        end_time_formatted = end_datetime.strftime("%d/%m %H:%M")
                        
                        # Format d'affichage du temps (style GSGUI: 0D 0H 0M 0S)
                        time_left_display = f"{days:d}D {hours:02d}H {minutes:02d}M {seconds:02d}S"
                        
                        # Format compatible avec notre interface + préserver les données originales
                        challenge = {
                            'id': str(challenge_data['id']),
                            'title': challenge_data['title'],
                            'url': challenge_data['url'],
                            'votes': int(challenge_data['member']['ranking']['total'].get('votes', 0)),
                            'rank': int(challenge_data['member']['ranking']['total'].get('rank', 0)),
                            'level': challenge_data['member']['ranking']['total'].get('level_name', 'UNKNOWN'),
                            'exposure': challenge_data['member']['ranking']['total'].get('exposure', 0),
                            'gps': 0,  # Placeholder
                            'time_left_days': timeleft['days'],
                            'time_left': {
                                'days': timeleft.get('days', 0),
                                'hours': timeleft.get('hours', 0),
                                'minutes': timeleft.get('minutes', 0),
                                'seconds': timeleft.get('seconds', 0)
                            },
                            'end_time': end_time_formatted,  # Format gs_backend_ui: "dd/mm HH:MM"
                            'time_left_display': time_left_display,  # Format gs_backend_ui: "0D 00H 00M 00S"
                            'time_left_seconds': time_left_seconds,  # Pour le tri (comme gs_backend_ui.py)
                            'selected_strategy': None,  # À implémenter
                            'turbo_status': 'none',  # Sera calculé après
                            '_original_data': challenge_data  # Préserver les données originales pour turbo status
                        }
                        
                        # Calculer le statut turbo avec la logique existante
                        challenge['turbo_status'] = determine_turbo_status(challenge, challenge_data)
                        challenges.append(challenge)
                        
                    except KeyError as e:
                        print(f"Error parsing challenge {challenge_data.get('id', 'unknown')}: {e}")
                        continue
                
                # Mettre à jour le cache global des titres
                update_challenge_titles_cache(challenges_cache)
                
                # Trier par temps restant croissant (comme gs_backend_ui.py)
                challenges.sort(key=lambda x: x['time_left_seconds'])
                log_with_profile(logger, "info", f"✅ Successfully processed {len(challenges)} real challenges (triés par temps restant)", profile_id)
                return challenges
                
    except Exception as e:
        print(f"❌ Error fetching real challenges: {e}")
        import traceback
        traceback.print_exc()
        return []

def load_challenge_strategies():
    """Charge les stratégies stockées depuis gsgui.ini organisées par profil (structure hiérarchique)"""
    try:
        with gsgui_ini_lock:
            config = ConfigObj(GSGUI_INI_PATH, encoding='utf-8')
            challenge_strategies_by_profile = {}
            
            if 'players' not in config:
                return {}
            
            # Parcourir tous les profils
            for profile_id, profile_data in config['players'].items():
                if isinstance(profile_data, dict) and 'scheduled_strategies' in profile_data:
                    profile_strategies = {}
                    for challenge_id, strategy_data in profile_data['scheduled_strategies'].items():
                        if isinstance(strategy_data, dict):
                            # Parser les actions depuis la structure hiérarchique
                            actions = []
                            for key, value in strategy_data.items():
                                if isinstance(value, dict) and key.startswith('action'):
                                    actions.append({
                                        'action': value.get('action', ''),
                                        'params': value.get('params', ''),
                                        'job_id': value.get('job_id', ''),
                                        'scheduled_at': value.get('scheduled_at', ''),
                                        'status': value.get('status', 'scheduled'),
                                        'result_message': value.get('result_message', ''),
                                        'executed_at': value.get('executed_at', '')
                                    })
                            
                            profile_strategies[challenge_id] = {
                                'strategy_name': strategy_data.get('strategy_name', ''),
                                'challenge_title': strategy_data.get('challenge_title', f'Challenge {challenge_id}'),
                                'strategy_status': strategy_data.get('strategy_status', 'active'),
                                'started_at': strategy_data.get('started_at', ''),
                                'actions': actions,
                                'profile_id': profile_id
                            }
                    
                    if profile_strategies:
                        challenge_strategies_by_profile[profile_id] = profile_strategies
            
            total_strategies = sum(len(strategies) for strategies in challenge_strategies_by_profile.values())
            total_actions = sum(
                len(strategy.get('actions', [])) 
                for strategies in challenge_strategies_by_profile.values() 
                for strategy in strategies.values()
            )
            print(f"📋 Loaded {total_strategies} hierarchical strategies with {total_actions} actions from gsgui.ini across {len(challenge_strategies_by_profile)} profiles")
            return challenge_strategies_by_profile
    except Exception as e:
        print(f"❌ Error loading hierarchical strategies: {e}")
        return {}

def save_challenge_strategy(challenge_id: str, strategy_name: str, scheduled_at: str, profile_id: str = "bruno", challenge_title: str = None):
    """Sauvegarde une stratégie pour un challenge dans gsgui.ini sous le profil"""
    try:
        # Récupérer le vrai titre du challenge s'il n'est pas fourni ou s'il est générique
        if not challenge_title or challenge_title == f"Challenge {challenge_id}" or challenge_title == challenge_id:
            try:
                # Récupérer le vrai titre depuis le cache ou l'API
                import asyncio
                real_title = asyncio.run(get_challenge_title(challenge_id, profile_id))
                if real_title and real_title != challenge_id:
                    challenge_title = real_title
                else:
                    challenge_title = f"Challenge {challenge_id}"
            except Exception as e:
                print(f"⚠️ Could not get challenge title for {challenge_id}: {e}")
                challenge_title = f"Challenge {challenge_id}"
        
        with gsgui_ini_lock:
            config = ConfigObj(GSGUI_INI_PATH, encoding='utf-8')
            
            # S'assurer que la structure existe
            if 'players' not in config:
                config['players'] = {}
            if profile_id not in config['players']:
                config['players'][profile_id] = {}
            if 'scheduled_strategies' not in config['players'][profile_id]:
                config['players'][profile_id]['scheduled_strategies'] = {}
            
            # Sauvegarder la stratégie sous le profil
            config['players'][profile_id]['scheduled_strategies'][challenge_id] = {
                'strategy_name': strategy_name,
                'challenge_title': challenge_title,
                'scheduled_at': scheduled_at
            }
            
            config.write()
            # Utiliser le titre fourni ou l'ID
            challenge_display_name = challenge_title if challenge_title else f"Challenge {challenge_id}"
            log_and_broadcast(f"💾 Saved strategy {strategy_name} for {challenge_display_name}", "success", profile_id)
            return True
    except Exception as e:
        error_msg = f"❌ Error saving challenge strategy: {e}"
        log_and_broadcast(error_msg, "error", profile_id)
        return False

def save_strategy_with_actions(challenge_id: str, strategy_name: str, actions: list, profile_id: str = "bruno", challenge_title: str = None):
    """Sauvegarde une stratégie avec sa structure hiérarchique complète d'actions dans gsgui.ini"""
    try:
        # Récupérer le vrai titre du challenge
        if not challenge_title or challenge_title == f"Challenge {challenge_id}" or challenge_title == challenge_id:
            try:
                import asyncio
                real_title = asyncio.run(get_challenge_title(challenge_id, profile_id))
                if real_title and real_title != challenge_id:
                    challenge_title = real_title
                else:
                    challenge_title = f"Challenge {challenge_id}"
            except Exception as e:
                print(f"⚠️ Could not get challenge title for {challenge_id}: {e}")
                challenge_title = f"Challenge {challenge_id}"
        
        with gsgui_ini_lock:
            config = ConfigObj(GSGUI_INI_PATH, encoding='utf-8')
            
            # S'assurer que la structure existe
            if 'players' not in config:
                config['players'] = {}
            if profile_id not in config['players']:
                config['players'][profile_id] = {}
            if 'scheduled_strategies' not in config['players'][profile_id]:
                config['players'][profile_id]['scheduled_strategies'] = {}
            
            # Créer la structure hiérarchique pour la stratégie
            strategy_data = {
                'strategy_name': strategy_name,
                'challenge_title': challenge_title,
                'strategy_status': 'active',
                'started_at': datetime.now().isoformat()
            }
            
            # Ajouter les actions avec leur structure complète
            for i, action in enumerate(actions):
                action_key = f"action{i+1}"
                strategy_data[action_key] = {
                    'action': action.get('action', ''),
                    'params': action.get('params', ''),
                    'job_id': action.get('job_id', ''),
                    'scheduled_at': action.get('scheduled_at', ''),
                    'status': action.get('status', 'scheduled'),
                    'result_message': action.get('result_message', ''),
                    'executed_at': action.get('executed_at', '')
                }
            
            # Sauvegarder la stratégie
            config['players'][profile_id]['scheduled_strategies'][challenge_id] = strategy_data
            config.write()
            
            challenge_display_name = challenge_title if challenge_title else f"Challenge {challenge_id}"
            log_and_broadcast(f"💾 Saved hierarchical strategy {strategy_name} with {len(actions)} actions for {challenge_display_name}", "success", profile_id)
            return True
            
    except Exception as e:
        error_msg = f"❌ Error saving hierarchical strategy: {e}"
        log_and_broadcast(error_msg, "error", profile_id)
        return False

def update_action_status(challenge_id: str, job_id: str, status: str, result_message: str = "", profile_id: str = "bruno"):
    """Met à jour le status d'une action spécifique dans gsgui.ini"""
    try:
        with gsgui_ini_lock:
            config = ConfigObj(GSGUI_INI_PATH, encoding='utf-8')
            
            if ('players' in config and profile_id in config['players'] and 
                'scheduled_strategies' in config['players'][profile_id] and
                challenge_id in config['players'][profile_id]['scheduled_strategies']):
                
                strategy_data = config['players'][profile_id]['scheduled_strategies'][challenge_id]
                
                # Chercher l'action avec ce job_id
                updated = False
                for key, value in strategy_data.items():
                    if isinstance(value, dict) and key.startswith('action') and value.get('job_id') == job_id:
                        value['status'] = status
                        value['result_message'] = result_message
                        if status in ['completed', 'failed']:
                            value['executed_at'] = datetime.now().isoformat()
                        updated = True
                        break
                
                if updated:
                    # Vérifier si toutes les actions sont terminées pour mettre à jour le status de la stratégie
                    all_actions_final = True
                    final_states = ['completed', 'failed', 'expired']
                    
                    for key, value in strategy_data.items():
                        if isinstance(value, dict) and key.startswith('action'):
                            if value.get('status') not in final_states:
                                all_actions_final = False
                                break
                    
                    if all_actions_final:
                        strategy_data['strategy_status'] = 'completed'
                        log_and_broadcast(f"✅ Strategy {strategy_data.get('strategy_name')} completed - all actions finished", "success", profile_id)
                    
                    config.write()
                    return True
                else:
                    print(f"⚠️ Job {job_id} not found in strategy {challenge_id}")
                    
        return False
        
    except Exception as e:
        error_msg = f"❌ Error updating action status: {e}"
        log_and_broadcast(error_msg, "error", profile_id)
        return False

def check_and_cleanup_completed_strategies(profile_id: str = "bruno"):
    """Vérifie et nettoie automatiquement les stratégies complètement terminées"""
    try:
        with gsgui_ini_lock:
            config = ConfigObj(GSGUI_INI_PATH, encoding='utf-8')
            
            if ('players' in config and profile_id in config['players'] and 
                'scheduled_strategies' in config['players'][profile_id]):
                
                strategies_to_remove = []
                strategies = config['players'][profile_id]['scheduled_strategies']
                
                for challenge_id, strategy_data in strategies.items():
                    if strategy_data.get('strategy_status') == 'completed':
                        strategies_to_remove.append(challenge_id)
                
                # Supprimer les stratégies complètes
                for challenge_id in strategies_to_remove:
                    strategy_name = strategies[challenge_id].get('strategy_name', 'unknown')
                    del strategies[challenge_id]
                    log_and_broadcast(f"🧹 Auto-cleaned completed strategy {strategy_name} for challenge {challenge_id}", "success", profile_id)
                
                if strategies_to_remove:
                    config.write()
                    return len(strategies_to_remove)
                    
        return 0
        
    except Exception as e:
        error_msg = f"❌ Error in auto-cleanup: {e}"
        log_and_broadcast(error_msg, "error", profile_id)
        return 0

def remove_challenge_strategy(challenge_id: str, profile_id: str = None):
    """Supprime une stratégie d'un challenge depuis gsgui.ini pour un profil donné"""
    try:
        with gsgui_ini_lock:
            config = ConfigObj(GSGUI_INI_PATH, encoding='utf-8')
            
            if 'players' not in config:
                return False
            
            # Si pas de profil spécifié, chercher dans tous les profils
            if profile_id is None:
                for pid, profile_data in config['players'].items():
                    if isinstance(profile_data, dict) and 'scheduled_strategies' in profile_data:
                        if challenge_id in profile_data['scheduled_strategies']:
                            del profile_data['scheduled_strategies'][challenge_id]
                            config.write()
                            log_and_broadcast(f"🗑️ Removed strategy for challenge {challenge_id} from profile {pid}", "info", pid)
                            return True
            else:
                # Supprimer pour un profil spécifique
                if profile_id in config['players'] and 'scheduled_strategies' in config['players'][profile_id]:
                    if challenge_id in config['players'][profile_id]['scheduled_strategies']:
                        del config['players'][profile_id]['scheduled_strategies'][challenge_id]
                        config.write()
                        log_and_broadcast(f"🗑️ Removed strategy for challenge {challenge_id}", "info", profile_id)
                        return True
            
            return False
    except Exception as e:
        error_msg = f"❌ Error removing challenge strategy: {e}"
        log_and_broadcast(error_msg, "error", profile_id)
        return False

# Fonction supprimée - plus de chargement des états turbo depuis .ini

def calculate_turbo_status(challenge_data: dict) -> str:
    """Calcule dynamiquement l'état turbo basé sur les données du challenge"""
    try:
        # Analyser l'état du challenge pour déterminer le status turbo
        # Statut stratégie
        turbo_data = challenge_data['member']['turbo']
        
        # Extraire le status depuis le dictionnaire turbo
        if isinstance(turbo_data, dict):
            turbo_status = turbo_data.get('status', 'none')
        else:
            turbo_status = str(turbo_data) if turbo_data else 'none'
            
        turbo_indicators = {
            "none": "",
            "running": "🟡 Running",
            "completed": "✅ OK",
            "failed": "❌ Failed",
            "timer": "⏰ Timer",
            "unknown": "❓ Unknown",
            "locked": "🔒 Locked",
            "free": "🆓 Free",
            "won": "🏆 Won",
            "used": "✅ Used"
        }
        turbo_text = turbo_indicators.get(turbo_status, "")

        return turbo_text
            
    except Exception as e:
        log_and_broadcast(f"❌ Error calculating turbo status: {e}", "error")
        return "unknown"

# Fonction supprimée - plus de persistence des états turbo

def get_real_turbo_status(challenge_data: Dict) -> str:
    """Extrait l'état turbo réel depuis les données GuruShots API"""
    try:
        # Vérifier member.turbo.state (structure officielle GuruShots)
        if 'member' in challenge_data and 'turbo' in challenge_data['member']:
            turbo_data = challenge_data['member']['turbo']
            if isinstance(turbo_data, dict) and 'state' in turbo_data:
                state = turbo_data['state']
                
                # Retourner l'état exact de l'API GuruShots
                if state in ["FREE", "WON", "USED", "LOCKED", "TIMER"]:
                    return state.lower()  # Convertir en minuscules pour cohérence
                
                # Gérer d'autres états possibles
                return state.lower()
        
        # Fallback: Si pas de données turbo dans member
        return "unknown"
        
    except Exception as e:
        print(f"❌ Error extracting turbo status: {e}")
        return "unknown"

def determine_turbo_status(challenge: Dict, challenge_data: Dict) -> str:
    """Détermine l'état turbo dynamiquement depuis les données API"""
    
    # 1. PRIORITÉ: États réels depuis l'API GuruShots
    api_status = get_real_turbo_status(challenge_data)
    if api_status in ["free", "won", "used", "locked", "timer"]:
        return api_status
    
    # 2. Fallback: Calcul dynamique basé sur les données du challenge
    calculated_status = calculate_turbo_status(challenge_data)
    if calculated_status != "unknown":
        return calculated_status
    
    # 3. Logique GSGUI intelligente basée sur le temps restant
    time_left = challenge.get('time_left', {})
    days = time_left.get('days', 0)
    
    # Si challenge fini ou presque fini
    if days == 0:
        hours = time_left.get('hours', 0)
        if hours <= 2:  # Moins de 2h restantes
            return "locked"  # Turbo verrouillé
    
    # Si challenge très récent (plus de 10 jours)
    if days > 10:
        return "timer"  # En attente du bon moment
    
    # Si on ne peut pas déterminer
    votes = challenge.get('votes', 0)
    if votes == 0:
        return "free"  # Disponible pour turbo
    
    # Par défaut, pas de turbo disponible
    return "none"


def get_real_boost_status(challenge_data: Dict) -> str:
    """Extrait l'état boost réel depuis les données GuruShots API avec temps restant"""
    try:
        # Vérifier member.boost.state (structure officielle GuruShots)
        #"boost": {
        #    "state": "AVAILABLE",
        #    "timeout": 1764324941
        #},
        if 'member' in challenge_data and 'boost' in challenge_data['member']:
            boost_data = challenge_data['member']['boost']
            if isinstance(boost_data, dict) and 'state' in boost_data:
                state = boost_data['state']
                timeout = boost_data.get('timeout')

                # Calculer le temps restant UNIQUEMENT si status est AVAILABLE et timeout not None
                time_remaining_str = ""
                if state == "AVAILABLE" and timeout is not None and isinstance(timeout, (int, float)):
                    import time
                    now = int(time.time())
                    remaining_seconds = timeout - now

                    if remaining_seconds > 0:
                        if remaining_seconds < 60:
                            time_remaining_str = f" ({remaining_seconds}s)"
                        elif remaining_seconds < 3600:
                            minutes = remaining_seconds // 60
                            time_remaining_str = f" ({minutes}m)"
                        else:
                            hours = remaining_seconds // 3600
                            minutes = (remaining_seconds % 3600) // 60
                            time_remaining_str = f" ({hours}h{minutes:02d}m)"
                    else:
                        time_remaining_str = " (expired)"

                # Retourner l'état avec le temps restant (seulement pour AVAILABLE)
                if state in ["LOCKED", "MISSED", "AVAILABLE", "USED"]:
                    result = state.lower() + time_remaining_str
                    print(f"🚀 Boost state: {state} | timeout: {timeout} | result: {result}")
                    return result

                # Gérer d'autres états possibles
                return state.lower()

        # Fallback: Si pas de données boost dans member
        return "unknown"

    except Exception as e:
        print(f"❌ Error extracting boost status: {e}")
        return "unknown"

def determine_boost_status(challenge: Dict, challenge_data: Dict) -> str:
    """Détermine l'état turbo dynamiquement depuis les données API"""

    # 1. PRIORITÉ: États réels depuis l'API GuruShots
    api_status = get_real_boost_status(challenge_data)
    return api_status


def get_user_token_from_config() -> Optional[str]:
    """Récupère le token depuis la config"""
    try:
        with gsgui_ini_lock:
            config = ConfigObj(GSGUI_INI_PATH, encoding='utf-8')
            if 'players' in config and config['players']:
                player = list(config['players'].keys())[0]
                return config['players'][player].get('xtoken')
    except Exception as e:
        print(f"❌ Error reading config: {e}")
    return None

# Routes
@app.get("/")
async def root():
    return {"message": "GSGUI Real API", "status": "running"}

@app.post("/api/v1/profiles/register", response_model=ProfileRegisterResponse)
async def register_profile(request: ProfileRegisterRequest):
    """Enregistre un profil - récupère automatiquement le x_token depuis gsgui.ini"""
    try:
        profile_id = request.profile_name.lower()
        
        # 1. Essayer de récupérer le x_token depuis gsgui.ini
        x_token = None
        try:
            from configobj import ConfigObj
            with gsgui_ini_lock:
                config = ConfigObj(GSGUI_INI_PATH, encoding='utf-8')
                if 'players' in config and profile_id in config['players']:
                    x_token = config['players'][profile_id].get('xtoken')
                    print(f"✅ Token trouvé pour {profile_id}: {x_token[:20] if x_token else 'None'}...")
                else:
                    print(f"⚠️ Profil {profile_id} non trouvé dans gsgui.ini")
        except Exception as e:
            print(f"❌ Erreur lecture gsgui.ini: {e}")
        
        # 2. Si pas de token dans .ini, utiliser celui fourni et le sauvegarder
        if not x_token and request.gs_token:
            x_token = request.gs_token
            print(f"✅ Utilisation token fourni: {x_token[:20]}...")
            
            # Sauvegarder le nouveau token dans gsgui.ini
            try:
                with gsgui_ini_lock:
                    config = ConfigObj(GSGUI_INI_PATH, encoding='utf-8')
                    if 'players' not in config:
                        config['players'] = {}
                    if profile_id not in config['players']:
                        config['players'][profile_id] = {}
                    
                    config['players'][profile_id]['xtoken'] = x_token
                    config.write()
                    print(f"✅ Token sauvegardé dans gsgui.ini pour {profile_id}")
            except Exception as e:
                print(f"❌ Erreur sauvegarde token dans .ini: {e}")
        
        # 3. Enregistrer le profil
        profiles[profile_id] = {
            "profile_name": request.profile_name, 
            "profile_id": profile_id,
            "gs_token": request.gs_token,  # Token fourni par l'UI
            "xtoken": x_token,  # Token récupéré depuis .ini
            "created_at": datetime.now().isoformat()
        }
        
        has_token = bool(x_token)
        status_msg = "Profile registered successfully"
        if not has_token:
            status_msg += " - Token manquant, récupération via cookies nécessaire"
        
        print(f"✅ Profil {request.profile_name} enregistré: token={'✅' if has_token else '❌'}")
        
        return ProfileRegisterResponse(
            profile_id=profile_id,
            profile_name=request.profile_name,
            status="created",
            message=status_msg,
            has_valid_token=has_token
        )
    except Exception as e:
        print(f"❌ Erreur enregistrement profil: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/challenges/")
async def get_challenges(profile_name: str):
    """Récupère les vrais challenges depuis GuruShots avec stratégies"""
    try:
        profile_id = profile_name.lower()
        print(f"🔍 Request for challenges from profile: {profile_name}")
        
        # Récupérer le profil et son x_token
        if profile_id not in profiles:
            raise HTTPException(status_code=404, detail=f"Profile {profile_name} not found. Please register first.")
        
        profile = profiles[profile_id]
        x_token = profile.get('xtoken')
        
        if not x_token:
            raise HTTPException(status_code=401, detail=f"No valid token for profile {profile_name}")
        
        print(f"🔍 Using token for {profile_name}: {x_token[:20]}...")
        
        # Récupérer les vrais challenges
        real_challenges = await fetch_real_challenges(x_token, profile_name.lower())
        
        if not real_challenges:
            print("⚠️ No real challenges, using config token...")
            # Fallback: essayer avec le token de la config
            config_token = get_user_token_from_config()
            if config_token:
                real_challenges = await fetch_real_challenges(config_token, profile_name.lower())
        
        # Charger les stratégies organisées par profil
        challenge_strategies_by_profile = load_challenge_strategies()
        
        # Obtenir les stratégies pour le profil actuel
        profile_strategies = challenge_strategies_by_profile.get(profile_name, {})
        
        # Enrichir les challenges avec leurs stratégies et états turbo
        for challenge in real_challenges:
            challenge_id = challenge['id']
            
            # Stratégies pour ce profil
            if challenge_id in profile_strategies:
                strategy_info = profile_strategies[challenge_id]
                challenge['selected_strategy'] = strategy_info['strategy_name']
                challenge['strategy_status'] = strategy_info['strategy_status']
            else:
                challenge['selected_strategy'] = None
                challenge['strategy_status'] = None
            
            # États turbo intelligents avec données originales
            original_data = challenge.get('_original_data', {})
            challenge['turbo_status'] = determine_turbo_status(challenge, original_data)
            # États boost intelligents avec données originales
            challenge['boost_status'] = determine_boost_status(challenge, original_data)

            # Nettoyer les données internes
            if '_original_data' in challenge:
                del challenge['_original_data']
            
            # Plus d'ID turbo persisté - calculé dynamiquement
            challenge['turbo_id'] = None
        
        print(f"📋 Returning {len(real_challenges)} challenges with strategies")
        return {"challenges": real_challenges}
        
    except Exception as e:
        print(f"❌ Error in get_challenges: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# AUTO-REFRESH ENDPOINTS
# ============================================================================

@app.post("/api/v1/challenges/{profile_id}/auto-refresh/toggle")
async def toggle_auto_refresh(
    profile_id: str,
    enabled: bool = Query(..., description="Enable or disable auto-refresh"),
    interval_minutes: int = Query(5, ge=1, le=60, description="Refresh interval in minutes")
):
    """Active/désactive l'auto-refresh global pour un profil"""
    try:
        from app.services.auto_refresh_scheduler import auto_refresh_scheduler

        if auto_refresh_scheduler is None:
            raise HTTPException(status_code=503, detail="Auto-refresh scheduler not initialized")

        if enabled:
            success = await auto_refresh_scheduler.enable_auto_refresh(profile_id, interval_minutes)
        else:
            success = await auto_refresh_scheduler.disable_auto_refresh(profile_id)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to toggle auto-refresh")

        status = auto_refresh_scheduler.get_status(profile_id)

        return {
            "success": True,
            "profile_id": profile_id,
            **status
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error toggling auto-refresh: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/challenges/{profile_id}/auto-refresh/status")
async def get_auto_refresh_status(profile_id: str):
    """Récupère le statut de l'auto-refresh pour un profil"""
    try:
        from app.services.auto_refresh_scheduler import auto_refresh_scheduler

        if auto_refresh_scheduler is None:
            raise HTTPException(status_code=503, detail="Auto-refresh scheduler not initialized")

        status = auto_refresh_scheduler.get_status(profile_id)

        return {
            "success": True,
            "profile_id": profile_id,
            **status
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error getting auto-refresh status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/profiles/{profile_id}/strategies")
async def schedule_strategy(profile_id: str, request: ScheduleStrategyRequest):
    """Programme une stratégie et la sauvegarde dans .ini"""
    try:
        strategy_id = f"{profile_id}_{request.challenge_id}_{int(datetime.now().timestamp())}"
        
        # Sauvegarder dans la mémoire (pour compatibilité)
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
        
        # NETTOYER D'ABORD l'ancienne stratégie si elle existe
        await cleanup_existing_strategy_for_challenge(request.challenge_id, profile_id)
        
        # Sauvegarder dans le fichier .ini (persistance)
        success = save_challenge_strategy(
            request.challenge_id, 
            request.strategy_name, 
            request.scheduled_at, 
            profile_id,
            request.challenge_title  # Passer le titre du challenge
        )
        
        if success:
            # PROGRAMMER RÉELLEMENT LA STRATÉGIE spécifique dans APScheduler
            await schedule_single_strategy(request.challenge_id, profile_id, request.challenge_title)
            
            # Utiliser le titre du challenge si disponible
            display_name = await get_challenge_title(request.challenge_id, profile_id)
            message = f"✅ Strategy {request.strategy_name} scheduled for {display_name}"
            log_and_broadcast(message, "success", profile_id)
        else:
            message = f"⚠️ Strategy scheduled in memory but failed to save to .ini"
            log_and_broadcast(message, "warning", profile_id)
        
        return {
            "strategy_id": strategy_id,
            "message": "Strategy scheduled successfully",
            "persisted": success
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
    """Annule une stratégie de la mémoire et du .ini"""
    try:
        cancelled_count = 0
        
        # Supprimer de la mémoire
        if strategy_id in strategies:
            challenge_id = strategies[strategy_id].get('challenge_id')
            del strategies[strategy_id]
            cancelled_count += 1
            
            # Supprimer du fichier .ini aussi
            if challenge_id:
                if remove_challenge_strategy(challenge_id):
                    print(f"🗑️ Strategy removed from .ini for challenge {challenge_id}")
        
        return {
            "message": "Strategy cancelled", 
            "cancelled_count": cancelled_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/v1/profiles/{profile_id}/strategies/{challenge_id}/clean")
async def clean_strategy_for_challenge(profile_id: str, challenge_id: str):
    """Nettoie complètement une stratégie pour un challenge (tous jobs + .ini)"""
    try:
        profile_id = profile_id.lower()
        
        if not STRATEGY_SCHEDULER_AVAILABLE:
            return {
                "success": False,
                "message": "StrategyScheduler non disponible",
                "removed_jobs": 0,
                "cleaned_ini": False
            }
        
        # 1. Supprimer TOUS les jobs APScheduler liés à ce challenge/profil 
        # (même les unlocked_boost en cours)
        jobs_removed = 0
        jobs = strategy_scheduler.scheduler.get_jobs()
        
        for job in jobs:
            # Ne pas toucher aux jobs système
            if job.id in ['precision_test', 'cleanup_expired_jobs']:
                continue
                
            # Supprimer tous les jobs qui contiennent le challenge_id
            if challenge_id in job.id and profile_id in job.id:
                try:
                    strategy_scheduler.scheduler.remove_job(job.id)
                    jobs_removed += 1
                    logger.info(f"🧹 Force removed job: {job.id}")
                except Exception as job_error:
                    logger.error(f"⚠️ Erreur suppression job {job.id}: {job_error}")
        
        # 2. Supprimer de gsgui.ini
        cleaned_ini = remove_challenge_strategy(challenge_id, profile_id)
        
        # 3. Supprimer de la mémoire
        memory_removed = 0
        strategies_to_remove = []
        for strategy_id, strategy_data in strategies.items():
            if (strategy_data.get('challenge_id') == challenge_id and 
                strategy_data.get('profile_id') == profile_id):
                strategies_to_remove.append(strategy_id)
        
        for strategy_id in strategies_to_remove:
            del strategies[strategy_id]
            memory_removed += 1
        
        cleanup_message = f"🧹 Stratégie forcément nettoyée pour challenge {challenge_id}: {jobs_removed} job(s), ini={cleaned_ini}, mémoire={memory_removed}"
        logger.info(cleanup_message)
        log_and_broadcast(cleanup_message, "cleanup", profile_id)
        
        return {
            "success": True,
            "message": f"Stratégie complètement nettoyée pour challenge {challenge_id}",
            "removed_jobs": jobs_removed,
            "cleaned_ini": cleaned_ini,
            "cleaned_memory": memory_removed,
            "challenge_id": challenge_id
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur clean_strategy_for_challenge: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/profiles/{profile_id}/turbo/execute")
async def execute_turbo_complete(profile_id: str, request: TurboExecutionRequest):
        """Exécute un turbo complet avec le système d'algorithmes sophistiqués"""
        import uuid

        # Générer un ID unique pour ce turbo (en dehors du try)
        turbo_id = str(uuid.uuid4())
        profile_id = profile_id.lower()

        try:
            from app.services.turbo_executor import turbo_executor

            # Récupérer le profil et son x_token
            if profile_id not in profiles:
                raise HTTPException(status_code=404, detail=f"Profile {profile_id} not found. Please register first.")

            profile = profiles[profile_id]
            x_token = profile.get('xtoken')
            request.algorithm = profile.get('turbo_algorithm')

            if not x_token:
                raise HTTPException(status_code=401, detail=f"No valid token for profile {profile_id}")

            print(f"🚀 Démarrage turbo pour profil {profile_id}: {x_token[:20]}...")
            log_and_broadcast(f"🚀 Démarrage turbo pour profil {profile_id}: {x_token[:20]}...", "info", profile_id)

            print(f"🚀 Démarrage turbo {turbo_id} pour challenge {request.challenge_id}")
            log_and_broadcast(f"🚀 Démarrage turbo {turbo_id} pour challenge {request.challenge_id}", "info", profile_id)

            print(f"   Algorithme: {request.algorithm or 'hybrid'}")
            log_and_broadcast(f"   Algorithme: {request.algorithm or 'hybrid'}", "info", profile_id)

            # Exécuter le turbo avec le système complet
            result = await turbo_executor.execute_turbo(
                profile_id=profile_id,
                turbo_id=turbo_id,
                challenge_id=request.challenge_id,
                challenge_title=request.challenge_title,
                challenge_time_left=request.challenge_time_left,
                algorithm=request.algorithm,
                xtoken=x_token
            )

            # Construire la réponse
            from datetime import datetime
            response = {
                "turbo_id": turbo_id,
                "profile_id": profile_id,
                "challenge_id": request.challenge_id,
                "challenge_title": request.challenge_title or f"Challenge {request.challenge_id}",
                "algorithm_used": request.algorithm or "hybrid",
                "execution_started_at": datetime.now().isoformat(),
                "execution_completed_at": datetime.now().isoformat(),
                "status": "completed" if result.get('success', False) else "failed",
                "success": result.get('success', False),
                "pairs_processed": result.get('pairs_processed', 0),
                "successful_pairs": result.get('successful_pairs', 0),
                "failed_pairs": result.get('failed_pairs', 0),
                "error_message": None if result.get('success', False) else "Turbo execution failed",
                "result_data": result
            }

            # Sauvegarder l'état final
            final_status = "completed" if result.get('success', False) else "failed"

            print(f"✅ Turbo {turbo_id} terminé: success={result.get('success', False)}")

            # Log et broadcast du résultat
            if result.get('success', False):
                log_and_broadcast(f"🎉 Turbo SUCCESS: {result.get('successful_pairs', 0)} paires réussies", "success", profile_id)
                
                # Envoyer challenge_update WebSocket pour refresh automatique après turbo success
                await connection_manager.notify_challenge_update(profile_id, {
                    "action": "turbo_completed",
                    "challenge_id": request.challenge_id,
                    "success": True,
                    "successful_pairs": result.get('successful_pairs', 0)
                })
            else:
                log_and_broadcast(f"❌ Turbo FAILED: {result.get('error_message', 'Unknown error')}", "error", profile_id)

            return response

        except Exception as e:
            print(f"❌ Error executing turbo: {e}")

            # Sauvegarder l'échec
            log_and_broadcast(f"❌ Turbo error: {str(e)}", "error", profile_id)

            raise HTTPException(status_code=500, detail=f"Error executing turbo: {str(e)}")


@app.post("/api/v1/challenges/simple-vote")
async def simple_vote(request: SimpleVoteRequest, profile_name: str):
    """Vote simple avec vrai API GuruShots"""
    try:
        print(f"🗳️ Simple vote request: {request.vote_count} votes for profile: {profile_name}")
        
        # Récupérer le profil via le service
        profile_id = profile_name.lower()
        profile = ProfileService.get_profile(profile_id)
        
        if not profile:
            raise HTTPException(status_code=404, detail=f"Profile {profile_name} not found. Please register first.")
        
        x_token = profile.get('xtoken')
        if not x_token:
            raise HTTPException(status_code=400, detail=f"No x_token found for profile {profile_name}")
        
        if REAL_VOTE_AVAILABLE:
            # Créer une instance GuruShotsAPI spécifique au profil
            profile_api = create_gurushots_api(x_token)
            if not profile_api:
                return []
            log_and_broadcast(f"🗳️ Exécution vote réel: {request.vote_count} votes sur {request.challenge_url}", "info", profile_name)
            
            result = await profile_api.execute_simple_vote(request.challenge_url, request.vote_count)
            
            if result.success:
                log_and_broadcast(f"✅ Vote réussi: {result.message}", "success", profile_name)
                return {
                    "success": True,
                    "message": result.message,
                    "result_data": {
                        "votes_cast": request.vote_count,
                        "challenge_url": request.challenge_url,
                        "exposure_gained": getattr(result, 'exposure_gained', 0)
                    }
                }
            else:
                log_and_broadcast(f"❌ Vote échoué: {result.message}", "error", profile_name)
                return {
                    "success": False,
                    "message": result.message,
                    "result_data": {}
                }
        else:
            # Fallback: simulation si service pas disponible
            log_and_broadcast(f"⚠️ Vote simulé (service réel indisponible): {request.vote_count} votes", "warning", profile_name)
            await asyncio.sleep(0.1)
            
            return {
                "success": True,
                "message": f"Successfully cast {request.vote_count} votes (simulated)",
                "result_data": {
                    "votes_cast": request.vote_count,
                    "challenge_url": request.challenge_url
                }
            }
            
    except Exception as e:
        error_msg = f"❌ Error during vote execution: {e}"
        log_and_broadcast(error_msg, "error", profile_name)
        return {
            "success": False,
            "message": str(e),
            "result_data": {}
        }

@app.post("/api/v1/actions/multi-vote")
async def multi_vote_challenges(request: MultiVoteRequest, profile_name: str):
    """Exécute des votes sur plusieurs challenges en utilisant simple-vote en interne"""
    try:
        print(f"🗳️ Multi-vote request: {request.votes_per_challenge} votes pour {len(request.challenge_ids)} challenge(s) - profil: {profile_name}")
        
        # Récupérer le profil
        profile_id = profile_name.lower()
        profile = ProfileService.get_profile(profile_id)
        
        if not profile:
            raise HTTPException(status_code=404, detail=f"Profile {profile_name} not found. Please register first.")
        
        success_count = 0
        failed_challenges = []
        results = []
        
        # Exécuter simple-vote pour chaque challenge
        for challenge_id in request.challenge_ids:
            try:
                challenge_url = challenge_id #f"https://gurushots.com/challenge/{challenge_id}"
                
                # Créer une requête simple-vote
                simple_request = SimpleVoteRequest(
                    challenge_url=challenge_url,
                    vote_count=request.votes_per_challenge
                )
                
                # Appeler la fonction simple-vote existante
                result = await simple_vote(simple_request, profile_name)
                
                if result.get("success", False):
                    success_count += 1
                    log_and_broadcast(f"✅ Multi-vote réussi: {challenge_id} ({request.votes_per_challenge} votes)", "success", profile_name)
                    results.append({
                        "challenge_id": challenge_id,
                        "success": True,
                        "message": result.get("message", "Vote réussi"),
                        "votes_cast": request.votes_per_challenge
                    })
                else:
                    failed_challenges.append(challenge_id)
                    error_msg = result.get("message", "Erreur inconnue")
                    log_and_broadcast(f"❌ Multi-vote échoué: {challenge_id} - {error_msg}", "error", profile_name)
                    results.append({
                        "challenge_id": challenge_id,
                        "success": False,
                        "message": error_msg,
                        "votes_cast": 0
                    })
                    
            except Exception as e:
                failed_challenges.append(challenge_id)
                error_msg = str(e)
                log_and_broadcast(f"❌ Erreur multi-vote {challenge_id}: {error_msg}", "error", profile_name)
                results.append({
                    "challenge_id": challenge_id,
                    "success": False,
                    "message": error_msg,
                    "votes_cast": 0
                })
        
        total_votes = success_count * request.votes_per_challenge
        summary_msg = f"✅ Multi-vote terminé: {success_count}/{len(request.challenge_ids)} challenges - {total_votes} votes au total"
        log_and_broadcast(summary_msg, "success", profile_name)
        
        return {
            "success": True,
            "message": summary_msg,
            "result_data": {
                "total_challenges": len(request.challenge_ids),
                "successful_votes": success_count,
                "failed_votes": len(failed_challenges),
                "votes_per_challenge": request.votes_per_challenge,
                "total_votes_cast": total_votes,
                "failed_challenge_ids": failed_challenges,
                "detailed_results": results
            }
        }
        
    except Exception as e:
        error_msg = f"❌ Erreur pendant multi-vote: {e}"
        log_and_broadcast(error_msg, "error", profile_name)
        return {
            "success": False,
            "message": str(e),
            "result_data": {}
        }

@app.post("/api/v1/actions/fill")
async def fill_challenges(request: FillRequest, profile_name: str):
    """Exécute fill sur plusieurs challenges en utilisant simple-vote (même logique que multi-vote)"""
    try:
        print(f"⚡ Fill request: {request.votes_per_challenge} votes pour {len(request.challenge_ids)} challenge(s) - profil: {profile_name}")
        
        # Utiliser la même logique que multi-vote en appelant simple-vote pour chaque challenge
        success_count = 0
        failed_challenges = []
        results = []
        
        # Récupérer le profil
        profile_id = profile_name.lower()
        profile = ProfileService.get_profile(profile_id)
        
        if not profile:
            raise HTTPException(status_code=404, detail=f"Profile {profile_name} not found. Please register first.")
        
        # Exécuter simple-vote pour chaque challenge (même logique que multi-vote)
        for challenge_id in request.challenge_ids:
            try:
                # Récupérer la vraie URL du challenge depuis les données (comme dans le turbo)
                challenge_data = None
                try:
                    # Récupérer les données du challenge via l'API GuruShots
                    profile_api = create_gurushots_api(profile.get('xtoken'))
                    if not profile_api:
                        print(f"⚠️ Could not create GuruShotsAPI for challenge {challenge_id}")
                        continue
                    
                    print(f"🔍 Calling get_challenges() for challenge {challenge_id}")
                    challenges_data = await profile_api.get_challenges()
                    print(f"🔍 get_challenges() returned successfully")

                except Exception as e:
                    print(f"⚠️ Could not fetch challenge data for {challenge_id}: {e}")
                    continue
                
                # challenges_data est une liste d'objets ChallengeData
                challenge_data = None
                if isinstance(challenges_data, list):
                    # Chercher le challenge avec l'ID correspondant
                    for challenge_obj in challenges_data:
                        if hasattr(challenge_obj, 'id') and str(challenge_obj.id) == str(challenge_id):
                            # Utiliser challenge_data qui contient le dict avec l'URL
                            challenge_data = challenge_obj.challenge_data if hasattr(challenge_obj, 'challenge_data') else {'id': challenge_obj.id, 'url': getattr(challenge_obj, 'url', None)}
                            print(f"✅ Found challenge {challenge_id} in list with URL: {challenge_data.get('url')}")
                            break
                    
                    if not challenge_data:
                        print(f"⚠️ Challenge {challenge_id} not found in list of {len(challenges_data)} challenges")
                        # Debug: afficher les IDs disponibles
                        available_ids = [getattr(c, 'id', 'N/A') for c in challenges_data[:5]]  # Premiers 5
                        print(f"🔍 Available IDs (first 5): {available_ids}")
                else:
                    print(f"⚠️ Unexpected challenges_data type: {type(challenges_data)}")
                    challenge_data = None
                
                # Utiliser la vraie URL ou fallback sur l'URL construite
                challenge_url = challenge_data.get('url') if challenge_data else challenge_id
                
                # Créer une requête simple-vote
                simple_request = SimpleVoteRequest(
                    challenge_url=challenge_url,
                    vote_count=request.votes_per_challenge
                )
                
                # Appeler la fonction simple-vote existante
                result = await simple_vote(simple_request, profile_name)
                
                if result.get("success", False):
                    success_count += 1
                    # Ne pas dupliquer les logs - simple_vote le fait déjà
                    results.append({
                        "challenge_id": challenge_id,
                        "success": True,
                        "message": result.get("message", "Vote réussi"),
                        "votes_cast": request.votes_per_challenge
                    })
                else:
                    failed_challenges.append(challenge_id)
                    error_msg = result.get("message", "Erreur inconnue")
                    # Ne pas dupliquer les logs - simple_vote le fait déjà
                    results.append({
                        "challenge_id": challenge_id,
                        "success": False,
                        "message": error_msg,
                        "votes_cast": 0
                    })
                    
            except Exception as e:
                failed_challenges.append(challenge_id)
                error_msg = str(e)
                # Log seulement les erreurs non gérées par simple_vote
                log_and_broadcast(f"❌ Erreur fill {challenge_id}: {error_msg}", "error", profile_name)
                results.append({
                    "challenge_id": challenge_id,
                    "success": False,
                    "message": error_msg,
                    "votes_cast": 0
                })
        
        total_votes = success_count * request.votes_per_challenge
        summary_msg = f"✅ Fill terminé: {success_count}/{len(request.challenge_ids)} challenges - {total_votes} votes au total"
        log_and_broadcast(summary_msg, "success", profile_name)
        
        # Envoyer challenge_update WebSocket pour refresh automatique après fill
        await connection_manager.notify_challenge_update(profile_name, {
            "action": "fill_completed",
            "success_count": success_count,
            "total_challenges": len(request.challenge_ids),
            "total_votes": total_votes
        })
        
        return {
            "success": True,
            "message": summary_msg,
            "result_data": {
                "total_challenges": len(request.challenge_ids),
                "successful_fills": success_count,
                "failed_fills": len(failed_challenges),
                "votes_per_challenge": request.votes_per_challenge,
                "total_votes_cast": total_votes,
                "failed_challenge_ids": failed_challenges,
                "detailed_results": results
            }
        }
        
    except Exception as e:
        error_msg = f"❌ Erreur pendant fill: {e}"
        log_and_broadcast(error_msg, "error", profile_name)
        return {
            "success": False,
            "message": str(e),
            "result_data": {}
        }


@app.post("/api/v1/challenges/turbo")
async def execute_turbo_complete(request: TurboExecutionRequest, profile_name: str):
    """Exécute un turbo complet avec le système d'algorithmes sophistiqués"""
    import uuid
    
    # Générer un ID unique pour ce turbo (en dehors du try)
    turbo_id = str(uuid.uuid4())
    profile_id = profile_name.lower()
    
    try:
        from app.services.turbo_executor import turbo_executor
        
        # Récupérer le profil et son x_token
        if profile_id not in profiles:
            raise HTTPException(status_code=404, detail=f"Profile {profile_name} not found. Please register first.")
        
        profile = profiles[profile_id]
        x_token = profile.get('xtoken')
        
        if not x_token:
            raise HTTPException(status_code=401, detail=f"No valid token for profile {profile_name}")
        
        print(f"🚀 Démarrage turbo pour profil {profile_name}: {x_token[:20]}...")
        log_and_broadcast(f"🚀 Démarrage turbo pour profil {profile_name}: {x_token[:20]}...", "info", profile_name)

        print(f"🚀 Démarrage turbo {turbo_id} pour challenge {request.challenge_id}")
        log_and_broadcast(f"🚀 Démarrage turbo {turbo_id} pour challenge {request.challenge_id}", "info", profile_name)

        print(f"   Algorithme: {request.algorithm or 'hybrid'}")
        log_and_broadcast(f"   Algorithme: {request.algorithm or 'hybrid'}", "info", profile_name)
        if request.algorythm == '':
            request.algorythm = "[hybrid,position_aware,adaptive_time]"
        # Exécuter le turbo avec le système complet
        result = await turbo_executor.execute_turbo(
            profile_id=profile_id,
            turbo_id=turbo_id,
            challenge_id=request.challenge_id,
            challenge_title=request.challenge_title,
            challenge_time_left=request.challenge_time_left,
            algorithm=request.algorythm ,
            xtoken=x_token
        )

        # Construire la réponse
        from datetime import datetime
        response = {
            "turbo_id": turbo_id,
            "profile_id": profile_id,
            "challenge_id": request.challenge_id,
            "challenge_title": request.challenge_title or f"Challenge {request.challenge_id}",
            "algorithm_used": request.algorithm or "hybrid",
            "execution_started_at": datetime.now().isoformat(),
            "execution_completed_at": datetime.now().isoformat(),
            "status": "completed" if result.get('success', False) else "failed",
            "success": result.get('success', False),
            "pairs_processed": result.get('pairs_processed', 0),
            "successful_pairs": result.get('successful_pairs', 0),
            "failed_pairs": result.get('failed_pairs', 0),
            "error_message": None if result.get('success', False) else "Turbo execution failed",
            "result_data": result
        }
        
        # Sauvegarder l'état final
        final_status = "completed" if result.get('success', False) else "failed"
        
        print(f"✅ Turbo {turbo_id} terminé: success={result.get('success', False)}")
        
        # Log et broadcast du résultat
        if result.get('success', False):
            log_and_broadcast(f"🎉 Turbo SUCCESS: {result.get('successful_pairs', 0)} paires réussies", "success", profile_name)
            
            # Envoyer challenge_update WebSocket pour refresh automatique après turbo success
            await connection_manager.notify_challenge_update(profile_name, {
                "action": "turbo_completed",  
                "challenge_id": request.challenge_id,
                "success": True,
                "successful_pairs": result.get('successful_pairs', 0)
            })
        else:
            log_and_broadcast(f"❌ Turbo FAILED: {result.get('error_message', 'Unknown error')}", "error", profile_name)
        
        return response
        
    except Exception as e:
        print(f"❌ Error executing turbo: {e}")
        
        # Sauvegarder l'échec
        log_and_broadcast(f"❌ Turbo error: {str(e)}", "error", profile_name)
        
        raise HTTPException(status_code=500, detail=f"Error executing turbo: {str(e)}")

def parse_strategy_actions(strategy_name: str) -> List[Dict]:
    """Parse les actions d'une stratégie depuis strategies.ini dans le format original"""
    try:
        with strategies_ini_lock:
            strategies_config = ConfigObj(os.path.join(os.path.dirname(__file__), "data", "strategies.ini"), encoding='utf-8')
            if strategy_name not in strategies_config:
                return []
            
            strategy_config = strategies_config[strategy_name]
            actions = []
            
            # Parser les actions numérotées (0, 1, 2, etc.)
            for key, value in strategy_config.items():
                if key == 'description':
                    continue
                
                # Les clés sont des numéros (0, 1, 2, etc.) et les valeurs sont du format:
                # "vote, end-4m0s,70" ou "end-4m0s,70" ou "vote,end-2m0s,80"
                if isinstance(value, str) and key.isdigit():
                    # Nettoyer la valeur en supprimant les guillemets si présents
                    clean_value = value.strip('"')
                    parts = [p.strip() for p in clean_value.split(',')]
                    
                    if len(parts) >= 2:
                        # Format: "action, timing, param" ou "timing, param" (vote implicite)
                        if len(parts) == 3:
                            action_type = parts[0]
                            timing = parts[1]
                            param_str = parts[2]
                        elif len(parts) == 2:
                            action_type = 'vote'
                            timing = parts[0]
                            param_str = parts[1]
                        else:
                            action_type = parts[0]
                            timing = parts[1]
                            params = str(parts[2:] if len(parts) > 2 else [])
                            #continue
                        
                        # Traitement différent selon le type d'action
                        if action_type.lower() == 'vote':
                            try:
                                vote_count = int(param_str)
                                # Ignorer les votes négatifs (-1) qui indiquent "pas de vote"
                                if vote_count > 0:
                                    actions.append({
                                        'action': 'vote',
                                        'timing': timing,
                                        'votes': vote_count,
                                        'raw': clean_value
                                    })
                            except ValueError:
                                print(f"⚠️ Invalid vote count in strategy {strategy_name}: {param_str}")
                                continue
                        elif action_type.lower() in ['boost', 'turbo', 'submit', 'swap']:
                            # Actions non-vote: boost, turbo, submit, swap
                            actions.append({
                                'action': action_type.lower(),
                                'timing': timing,
                                'parameter': param_str,  # Photo ID, index, etc.
                                'raw': clean_value
                            })
                        else:
                            print(f"⚠️ Unknown action type in strategy {strategy_name}: {action_type}")
                            continue
            
            return actions
    except Exception as e:
        print(f"❌ Error parsing strategy {strategy_name}: {e}")
        return []










@app.get("/api/v1/strategies/active")
async def get_active_strategies(profile_name: Optional[str] = None):
    """Récupère les stratégies actives depuis APScheduler ET ExtendedStrategyExecutor"""
    try:
        # Nouvelle implémentation : interroger APScheduler + ExtendedStrategyExecutor
        detailed_strategies = []
        total_jobs = 0
        
        # 1. Récupérer les jobs APScheduler actifs
        apscheduler_jobs = []
        try:
            if STRATEGY_SCHEDULER_AVAILABLE:
                from app.services.strategy_scheduler import strategy_scheduler
                if strategy_scheduler._running:
                    jobs = strategy_scheduler.scheduler.get_jobs()
                    for job in jobs:
                        # Extraire les informations utiles du job
                        job_args = job.args if hasattr(job, 'args') else []
                        
                        # Déterminer le type de job
                        job_type = 'unknown'
                        challenge_id = None
                        strategy_name = None
                        profile_id = None
                        
                        if job.id.startswith('extended_'):
                            job_type = 'extended_action'
                            # Format: extended_strategy_challenge_timestamp_action_index_actiontype
                            parts = job.id.split('_')
                            if len(parts) >= 3:
                                strategy_name = parts[1] if len(parts) > 1 else 'unknown'
                                challenge_id = parts[2] if len(parts) > 2 else 'unknown'
                        elif len(job_args) >= 4:
                            # Format standard: [profile_id, strategy_id, challenge_id, strategy_name]
                            job_type = 'scheduled_strategy'
                            profile_id = job_args[0] if job_args else 'unknown'
                            challenge_id = job_args[2] if len(job_args) > 2 else 'unknown'
                            strategy_name = job_args[3] if len(job_args) > 3 else 'unknown'
                        
                        job_info = {
                            'id': job.id,
                            'name': job.name or str(job.id),
                            'next_run': job.next_run_time.isoformat() if job.next_run_time else None,
                            'next_run_time_exact': job.next_run_time.strftime('%H:%M:%S') if job.next_run_time else None,
                            'next_run_date': job.next_run_time.strftime('%Y-%m-%d') if job.next_run_time else None,
                            'trigger': str(job.trigger),
                            'args': job_args,
                            'source': 'apscheduler',
                            'job_type': job_type,
                            'challenge_id': challenge_id,
                            'strategy_name': strategy_name,
                            'profile_id': profile_id
                        }
                        apscheduler_jobs.append(job_info)
                        total_jobs += 1
                    logger.info(f"✅ Found {len(apscheduler_jobs)} APScheduler jobs")
        except Exception as e:
            logger.error(f"❌ Error getting APScheduler jobs: {e}")
        
        # 2. Récupérer les stratégies Extended actives
        extended_strategies = []
        try:
            from app.services.extended_strategy_executor import extended_strategy_executor
            for execution_id, context in extended_strategy_executor.active_executions.items():
                if context['status'] == 'active':
                    strategy_info = {
                        'execution_id': execution_id,
                        'challenge_id': context['challenge_id'],
                        'strategy_name': context['strategy_name'],
                        'profile_id': context['profile_id'],
                        'started_at': context['started_at'].isoformat(),
                        'status': context['status'],
                        'actions': context['actions'],
                        'source': 'extended_executor'
                    }
                    extended_strategies.append(strategy_info)
                    total_jobs += len(context.get('actions', []))
            logger.info(f"✅ Found {len(extended_strategies)} Extended strategies active")
        except Exception as e:
            logger.error(f"❌ Error getting Extended strategies: {e}")
        
        # 3. Récupérer le mapping des challenges pour les titres
        challenges_map = {}
        if profile_name:
            try:
                profile_id = profile_name.lower()
                if profile_id in profiles:
                    x_token = profiles[profile_id].get('xtoken')
                    if x_token:
                        real_challenges = await fetch_real_challenges(x_token, profile_id)
                        challenges_map = {str(ch['id']): ch['title'] for ch in real_challenges}
                        logger.info(f"✅ Mapping {len(challenges_map)} challenge titles")
            except Exception as e:
                logger.error(f"⚠️ Could not fetch challenge titles: {e}")
        
        # 4. Formater les résultats
        for job in apscheduler_jobs:
            # Filtrer par profil si spécifié
            if profile_name and len(job.get('args', [])) > 0:
                job_profile = job['args'][0] if job['args'] else ''
                if job_profile != profile_name.lower():
                    continue
            
            # Récupérer le titre du challenge si possible
            job_challenge_title = 'Unknown Challenge'
            if job.get('challenge_id') and challenges_map:
                job_challenge_title = challenges_map.get(
                    str(job['challenge_id']), 
                    f"Challenge {job['challenge_id']}"
                )
            
            detailed_strategies.append({
                'type': 'scheduled',
                'source': 'apscheduler',
                'job_id': job['id'],
                'name': job['name'],
                'next_execution': job['next_run'],
                'exact_execution_time': job['next_run_time_exact'],
                'execution_date': job['next_run_date'],
                'trigger': job['trigger'],
                'status': 'scheduled',
                'job_type': job.get('job_type', 'unknown'),
                'challenge_id': job.get('challenge_id'),
                'challenge_title': job_challenge_title,
                'strategy_name': job.get('strategy_name'),
                'profile_id': job.get('profile_id')
            })
        
        for strategy in extended_strategies:
            # Filtrer par profil si spécifié
            if profile_name and strategy['profile_id'] != profile_name.lower():
                continue
            
            challenge_title = challenges_map.get(
                str(strategy['challenge_id']), 
                f"Challenge {strategy['challenge_id']}"
            )
            
            detailed_strategies.append({
                'type': 'extended',
                'source': 'extended_executor',
                'execution_id': strategy['execution_id'],
                'challenge_id': strategy['challenge_id'],
                'challenge_title': challenge_title,
                'strategy_name': strategy['strategy_name'],
                'profile_id': strategy['profile_id'],
                'started_at': strategy['started_at'],
                'status': strategy['status'],
                'actions_count': len(strategy.get('actions', [])),
                'actions': strategy.get('actions', [])
            })
        
        return {
            "strategies": detailed_strategies,
            "total_count": len(detailed_strategies),
            "total_jobs": total_jobs,
            "apscheduler_jobs": len(apscheduler_jobs),
            "extended_strategies": len(extended_strategies),
            "source": "apscheduler_real_time"
        }
        
    except Exception as e:
        print(f"❌ Error getting active strategies: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/scheduler/status")
async def get_scheduler_status():
    """Retourne le statut et les métriques de précision d'APScheduler"""
    try:
        if not STRATEGY_SCHEDULER_AVAILABLE:
            return {
                "running": False,
                "error": "StrategyScheduler service not available"
            }
        
        from app.services.strategy_scheduler import strategy_scheduler
        
        if not strategy_scheduler._running:
            return {
                "running": False,
                "scheduler_state": "stopped"
            }
        
        # Récupérer les jobs actifs avec leurs timing
        jobs = strategy_scheduler.scheduler.get_jobs()
        job_details = []
        
        for job in jobs:
            next_run = job.next_run_time
            now = datetime.now()
            
            if next_run:
                time_until_run = (next_run - now).total_seconds()
                job_info = {
                    "id": job.id,
                    "name": job.name,
                    "next_run": next_run.isoformat(),
                    "next_run_exact_time": next_run.strftime('%H:%M:%S'),
                    "seconds_until_run": round(time_until_run, 1),
                    "trigger_type": str(job.trigger),
                    "misfire_grace_time": getattr(job, 'misfire_grace_time', 'default'),
                    "coalesce": getattr(job, 'coalesce', 'default'),
                    "max_instances": getattr(job, 'max_instances', 'default')
                }
                job_details.append(job_info)
        
        return {
            "running": True,
            "scheduler_state": "active",
            "total_jobs": len(jobs),
            "active_jobs": job_details,
            "scheduler_config": {
                "timezone": str(strategy_scheduler.scheduler.timezone),
                "jobstore_type": "MemoryJobStore",
                "executor_type": "AsyncIOExecutor"
            },
            "precision_monitoring": True,
            "current_time": datetime.now().isoformat(),
            "current_time_exact": datetime.now().strftime('%H:%M:%S.%f')
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting scheduler status: {e}")
        return {
            "running": False,
            "error": str(e)
        }

@app.post("/api/v1/scheduler/cleanup")
async def cleanup_scheduler_jobs():
    """Nettoie les jobs expirés d'APScheduler"""
    try:
        if not STRATEGY_SCHEDULER_AVAILABLE:
            return {
                "success": False,
                "error": "StrategyScheduler service not available"
            }
        
        from app.services.strategy_scheduler import strategy_scheduler
        
        if not strategy_scheduler._running:
            return {
                "success": False,
                "error": "Scheduler is not running"
            }
        
        # Appeler la méthode de nettoyage
        cleanup_result = strategy_scheduler.cleanup_expired_jobs()
        
        logger.info(f"🧹 Manual cleanup completed: {cleanup_result.get('cleaned_count', 0)} jobs removed")
        
        return cleanup_result
        
    except Exception as e:
        logger.error(f"❌ Error during manual cleanup: {e}")
        return {
            "success": False,
            "error": str(e),
            "cleaned_count": 0
        }

@app.post("/api/v1/scheduler/deep-purge")
async def deep_purge_scheduler_and_strategies(profile_id: str = "all"):
    """
    Purge profonde : supprime TOUS les jobs APScheduler et stratégies du .ini
    Paramètres:
    - profile_id: "all" pour tous les profils, ou un profil spécifique (ex: "bruno")
    """
    try:
        if not STRATEGY_SCHEDULER_AVAILABLE:
            return {
                "success": False,
                "error": "StrategyScheduler service not available"
            }
        
        from app.services.strategy_scheduler import strategy_scheduler
        
        if not strategy_scheduler._running:
            return {
                "success": False,
                "error": "Scheduler is not running"
            }
        
        purge_result = {
            "success": True,
            "apscheduler_jobs_removed": 0,
            "ini_strategies_removed": 0,
            "profiles_processed": [],
            "errors": []
        }
        
        # 1. PURGE APScheduler - Supprimer TOUS les jobs (sauf système)
        jobs = strategy_scheduler.get_jobs()
        for job in jobs:
            # Préserver uniquement les jobs système
            if job.id in ['precision_test', 'cleanup_expired_jobs']:
                continue
            
            # Si un profil spécifique est demandé, filtrer par profil
            if profile_id != "all":
                if not job.id.startswith(f"{profile_id}_"):
                    continue
            
            try:
                strategy_scheduler.scheduler.remove_job(job.id)
                purge_result["apscheduler_jobs_removed"] += 1
                logger.info(f"🗑️ Removed APScheduler job: {job.id}")
            except Exception as e:
                error_msg = f"Error removing job {job.id}: {e}"
                purge_result["errors"].append(error_msg)
                logger.error(error_msg)
        
        # 2. PURGE gsgui.ini - Supprimer toutes les stratégies
        profiles_to_process = [profile_id] if profile_id != "all" else list(profiles.keys())
        
        for pid in profiles_to_process:
            try:
                purge_result["profiles_processed"].append(pid)
                
                # Charger directement le fichier de configuration
                config_file_path = GSGUI_INI_PATH
                config = ConfigObj(config_file_path, encoding='utf-8')
                
                if pid not in config:
                    continue
                
                strategies_removed = 0
                user_config = config[pid]
                
                # Supprimer toutes les stratégies programmées
                if 'scheduled_strategies' in user_config:
                    strategies_count = len(user_config['scheduled_strategies'])
                    user_config['scheduled_strategies'] = {}
                    strategies_removed += strategies_count
                
                # Supprimer toutes les stratégies hiérarchiques
                sections_to_remove = []
                for section_name in user_config.keys():
                    if section_name.startswith('[[[[') and section_name.endswith(']]]]'):
                        sections_to_remove.append(section_name)
                
                for section_name in sections_to_remove:
                    del user_config[section_name]
                    strategies_removed += 1
                
                # Sauvegarder les modifications
                config.write()
                
                purge_result["ini_strategies_removed"] += strategies_removed
                logger.info(f"🗑️ Removed {strategies_removed} strategies from {pid} profile")
                
            except Exception as e:
                error_msg = f"Error purging strategies for profile {pid}: {e}"
                purge_result["errors"].append(error_msg)
                logger.error(error_msg)
        
        # 3. Logs de résumé
        logger.info(f"🧹 DEEP PURGE COMPLETED:")
        logger.info(f"  - APScheduler jobs removed: {purge_result['apscheduler_jobs_removed']}")
        logger.info(f"  - INI strategies removed: {purge_result['ini_strategies_removed']}")
        logger.info(f"  - Profiles processed: {purge_result['profiles_processed']}")
        if purge_result["errors"]:
            logger.warning(f"  - Errors encountered: {len(purge_result['errors'])}")
        
        return purge_result
        
    except Exception as e:
        logger.error(f"❌ Error during deep purge: {e}")
        return {
            "success": False,
            "error": str(e),
            "apscheduler_jobs_removed": 0,
            "ini_strategies_removed": 0
        }

@app.get("/api/v1/scheduler/detailed-status")
async def get_detailed_scheduler_status():
    """Retourne le statut détaillé avec compteurs de jobs actifs/expirés"""
    try:
        if not STRATEGY_SCHEDULER_AVAILABLE:
            return {
                "success": False,
                "error": "StrategyScheduler service not available"
            }
        
        from app.services.strategy_scheduler import strategy_scheduler
        
        if not strategy_scheduler._running:
            return {
                "success": False,
                "error": "Scheduler is not running"
            }
        
        # Appeler la méthode de statut détaillé
        status_result = strategy_scheduler.get_scheduler_status()
        
        return {
            "success": True,
            **status_result
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting detailed scheduler status: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@app.get("/api/v1/scheduler/strategies")
async def get_strategies_status():
    """Retourne le statut organisé par stratégies (nouvelle structure hiérarchique)"""
    try:
        if not STRATEGY_SCHEDULER_AVAILABLE:
            return {
                "success": False,
                "message": "StrategyScheduler non disponible",
                "scheduler_running": False,
                "total_strategies": 0,
                "total_jobs": 0,
                "strategies": {},
                "system_jobs": []
            }
        
        from app.services.strategy_scheduler import strategy_scheduler
        
        if not strategy_scheduler._running:
            return {
                "success": False,
                "error": "Scheduler is not running",
                "scheduler_running": False,
                "total_strategies": 0,
                "total_jobs": 0,
                "strategies": {},
                "system_jobs": []
            }
        
        # Appeler la nouvelle méthode de statut par stratégies
        strategies_result = strategy_scheduler.get_strategies_status()
        
        return {
            "success": True,
            **strategies_result
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting strategies status: {e}")
        return {
            "success": False,
            "error": str(e),
            "scheduler_running": False,
            "total_strategies": 0,
            "total_jobs": 0,
            "strategies": {},
            "system_jobs": []
        }

@app.delete("/api/v1/scheduler/jobs/all")
async def clear_all_scheduler_jobs():
    """Supprime TOUS les jobs d'APScheduler (sauf système)"""
    try:
        if not STRATEGY_SCHEDULER_AVAILABLE:
            return {
                "success": False,
                "message": "StrategyScheduler non disponible",
                "removed_jobs": 0
            }
        
        # Récupérer tous les jobs APScheduler
        jobs = strategy_scheduler.scheduler.get_jobs()
        
        # Filtrer pour garder seulement les jobs système
        system_jobs = ['Precision Test Job', 'Cleanup Expired Jobs']
        jobs_to_remove = []
        
        for job in jobs:
            if job.name not in system_jobs:
                jobs_to_remove.append(job)
        
        # Supprimer les jobs non-système
        removed_count = 0
        for job in jobs_to_remove:
            try:
                strategy_scheduler.scheduler.remove_job(job.id)
                logger.info(f"🧹 Removed APScheduler job: {job.id}")
                removed_count += 1
            except Exception as e:
                logger.error(f"❌ Error removing job {job.id}: {e}")
        
        logger.info(f"✅ Cleared {removed_count} APScheduler jobs, kept {len(system_jobs)} system jobs")
        
        return {
            "success": True,
            "message": f"Supprimé {removed_count} jobs APScheduler",
            "removed_jobs": removed_count,
            "kept_system_jobs": len(system_jobs)
        }
        
    except Exception as e:
        logger.error(f"❌ Error clearing APScheduler jobs: {e}")
        return {
            "success": False,
            "error": str(e),
            "removed_jobs": 0
        }

@app.get("/api/v1/profiles")
async def get_profiles():
    """Récupère la liste des profils depuis gsgui.ini"""
    try:
        with gsgui_ini_lock:
            gsgui_ini_path = GSGUI_INI_PATH
            config = ConfigObj(gsgui_ini_path, encoding='utf-8')
            
            profiles_data = []
            if 'players' in config:
                for profile_name, profile_data in config['players'].items():
                    profiles_data.append({
                        'name': profile_name,
                        'has_token': bool(profile_data.get('xtoken')),
                        'turbo_algorithm': profile_data.get('turbo_algorithm', ''),
                        'auto_optimize_turbo': profile_data.get('auto_optimize_turbo', False)
                    })
        
        return {"profiles": profiles_data}
        
    except Exception as e:
        print(f"❌ Error getting profiles: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/profiles/add")
async def add_profile(profile_name: str, xtoken: str):
    """Ajoute un nouveau profil dans gsgui.ini"""
    try:
        with gsgui_ini_lock:
            gsgui_ini_path = GSGUI_INI_PATH
            config = ConfigObj(gsgui_ini_path, encoding='utf-8')
            
            # Créer la section players si elle n'existe pas
            if 'players' not in config:
                config['players'] = {}
            
            # Ajouter le profil
            config['players'][profile_name] = {
                'xtoken': xtoken,
                'turbo_algorithm': "[hybrid,position_aware,adaptive_time]",
                'auto_optimize_turbo': False
            }
            
            # Ajouter la section scheduled_strategies vide
            config['players'][profile_name]['scheduled_strategies'] = {}
            
            config.write()
        
        # Enregistrer aussi dans le système de profils en mémoire
        profiles[profile_name.lower()] = {'xtoken': xtoken}
        
        print(f"✅ Profil {profile_name} ajouté avec succès")
        return {"status": "success", "message": f"Profil {profile_name} ajouté"}
        
    except Exception as e:
        print(f"❌ Error adding profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/strategies/list")
async def get_strategies_list():
    """Récupère la liste des noms de stratégies depuis strategies.ini"""
    try:
        strategies_ini_path = os.path.join(os.path.dirname(__file__), "data", "strategies.ini")
        
        if not os.path.exists(strategies_ini_path):
            raise HTTPException(status_code=404, detail="Fichier strategies.ini non trouvé")
        
        with strategies_ini_lock:
            config = ConfigObj(strategies_ini_path, encoding='utf-8')
            
            strategies_list = []
            for strategy_name, strategy_data in config.items():
                if isinstance(strategy_data, dict):  # Vérifier que c'est une section de stratégie
                    description = strategy_data.get('description', f'Stratégie {strategy_name}')
                    strategies_list.append({
                        'name': strategy_name,
                        'description': description
                    })
        
        return {"strategies": strategies_list}
        
    except Exception as e:
        print(f"❌ Error getting strategies list: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/strategies/config")
async def get_strategies_config():
    """Récupère le contenu du fichier strategies.ini"""
    try:
        strategies_ini_path = os.path.join(os.path.dirname(__file__), "data", "strategies.ini")
        
        with strategies_ini_lock:
            with open(strategies_ini_path, 'r', encoding='utf-8') as f:
                content = f.read()
        
        return {"content": content, "path": strategies_ini_path}
        
    except Exception as e:
        print(f"❌ Error getting strategies config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/strategies/config")
async def update_strategies_config(request: dict):
    """Met à jour le fichier strategies.ini"""
    try:
        # Extraire le contenu de la requête JSON
        content = request.get("content", "")
        if not content:
            raise HTTPException(status_code=400, detail="Missing content field")
            
        strategies_ini_path = os.path.join(os.path.dirname(__file__), "data", "strategies.ini")
        
        with strategies_ini_lock:
            # Sauvegarder le fichier original
            import shutil
            backup_path = strategies_ini_path + ".backup"
            shutil.copy2(strategies_ini_path, backup_path)
            
            # Écrire le nouveau contenu
            with open(strategies_ini_path, 'w', encoding='utf-8') as f:
                f.write(content)
        
        print(f"✅ Strategies.ini mis à jour (backup: {backup_path})")
        
        # Recharger la configuration dans ExtendedStrategyExecutor
        from app.services.extended_strategy_executor import extended_strategy_executor
        reload_success = extended_strategy_executor.reload_config()
        
        if reload_success:
            print("✅ Configuration ExtendedStrategyExecutor rechargée")
        else:
            print("⚠️ Échec du rechargement ExtendedStrategyExecutor")
        
        return {"status": "success", "message": "Fichier strategies.ini mis à jour", "backup": backup_path}
        
    except Exception as e:
        print(f"❌ Error updating strategies config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/v1/strategies/cleanup")
async def cleanup_strategies_endpoint(profile_name: Optional[str] = None):
    """Nettoie les stratégies obsolètes et expirées"""
    try:
        print(f"🧹 API Cleanup demandé pour profil: {profile_name or 'tous'}")
        
        if profile_name:
            # Cleanup pour un profil spécifique
            profile_id = profile_name.lower()
            cleanup_count = await cleanup_expired_strategies_for_profile(profile_id)
        else:
            # Cleanup global pour tous les profils
            cleanup_count = await cleanup_expired_strategies_global()
        
        return {
            "status": "success",
            "message": f"✅ {cleanup_count} stratégie(s) obsolète(s) nettoyée(s)",
            "cleaned_count": cleanup_count
        }
        
    except Exception as e:
        print(f"❌ Error cleanup strategies: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/logs/{log_type}")
async def get_logs(log_type: str):
    """
    Récupère le contenu d'un fichier de log
    
    Args:
        log_type: Type de log (backend, frontend, manager)
        
    Returns:
        Contenu du fichier de log en texte brut
    """
    from fastapi.responses import PlainTextResponse
    from pathlib import Path
    
    try:
        # Chemin vers le répertoire logs (au niveau racine du projet)
        logs_dir = Path(__file__).parent.parent / "logs"
        
        if log_type == "backend":
            log_file = logs_dir / "backend.log"
        elif log_type == "frontend":
            log_file = logs_dir / "frontend.log" 
        elif log_type == "manager":
            log_file = logs_dir / "manager.log"
        else:
            raise HTTPException(status_code=400, detail=f"Type de log non supporté: {log_type}")
        
        if not log_file.exists():
            return PlainTextResponse(
                content=f"# Fichier de log non trouvé\n# Chemin: {log_file}\n# Le fichier sera créé au démarrage de l'application",
                status_code=200
            )
        
        # Lire le fichier de log
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Limiter la taille si le fichier est trop gros (max 5MB)
        max_size = 5 * 1024 * 1024  # 5MB
        if len(content) > max_size:
            # Prendre les dernières lignes pour rester dans la limite
            lines = content.split('\n')
            truncated_lines = []
            current_size = 0
            
            # Partir de la fin et remonter
            for line in reversed(lines):
                line_size = len(line) + 1  # +1 pour le \n
                if current_size + line_size > max_size:
                    break
                truncated_lines.append(line)
                current_size += line_size
            
            # Remettre dans l'ordre et ajouter un message d'info
            truncated_lines.reverse()
            content = "# Fichier tronqué - seules les dernières lignes sont affichées\n" + '\n'.join(truncated_lines)
        
        return PlainTextResponse(
            content=content,
            status_code=200,
            headers={"Content-Type": "text/plain; charset=utf-8"}
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la lecture du fichier de log: {str(e)}"
        )

@app.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    """WebSocket endpoint pour les logs en temps réel"""
    await websocket.accept()
    websocket_connections.add(websocket)
    
    try:
        # Envoyer un message de bienvenue
        welcome_data = {
            "timestamp": datetime.now().isoformat(),
            "type": "info",
            "message": "🔌 Connexion WebSocket établie - Logs en temps réel activés"
        }
        await websocket.send_text(json.dumps(welcome_data))
        
        # Garder la connexion ouverte
        while True:
            try:
                # Écouter les messages du client (même si on n'en fait rien pour l'instant)
                await websocket.receive_text()
            except WebSocketDisconnect:
                break
                
    except WebSocketDisconnect:
        pass
    finally:
        websocket_connections.discard(websocket)
        print(f"🔌 WebSocket disconnected. Active connections: {len(websocket_connections)}")

@app.websocket("/ws/logs/{profile_id}")
async def websocket_logs_profile(websocket: WebSocket, profile_id: str):
    """WebSocket endpoint pour les logs d'un profil spécifique"""
    profile_id = profile_id.lower()
    
    # Enregistrer la connexion dans le connection_manager pour ce profil (qui gère accept())
    try:
        await connection_manager.connect(websocket, profile_id)
        
        # Envoyer un message de bienvenue
        welcome_data = {
            "timestamp": datetime.now().isoformat(),
            "type": "info", 
            "message": f"🔌 Connexion WebSocket établie pour profil {profile_id}"
        }
        await websocket.send_text(json.dumps(welcome_data))
        
        # Garder la connexion ouverte
        while True:
            try:
                await websocket.receive_text()
            except WebSocketDisconnect:
                break
    except WebSocketDisconnect:
        pass
    finally:
        connection_manager.disconnect(websocket, profile_id)
        print(f"🔌 WebSocket disconnected for profile {profile_id}")

# NOTE: schedule_existing_strategies() supprimée - remplacée par startup_event()

async def schedule_strategies_from_ini():
    """Programme les stratégies depuis gsgui.ini avec APScheduler"""
    try:
        print("📋 Loading strategies from gsgui.ini...")
        challenge_strategies_by_profile = load_challenge_strategies()
        
        if not challenge_strategies_by_profile:
            print("📋 No strategies to schedule")
            return
        
        scheduled_count = 0
        for profile_id, profile_strategies in challenge_strategies_by_profile.items():
            active_strategies = {k: v for k, v in profile_strategies.items() if v.get('strategy_status', 'active') == 'active'}
            print(f"🎯 Processing {len(active_strategies)} active strategies for profile {profile_id} (skipping {len(profile_strategies) - len(active_strategies)} completed)")
            for challenge_id, strategy_info in active_strategies.items():
                strategy_name = strategy_info['strategy_name']
                challenge_title = strategy_info.get('challenge_title', f'Challenge {challenge_id}')
                print(f"  - Challenge {challenge_id}: strategy {strategy_name}")
                
                try:
                    # PROGRAMMER RÉELLEMENT chaque stratégie trouvée
                    print(f"🚀 Scheduling strategy '{strategy_name}' for challenge {challenge_id} (profile: {profile_id})")
                    execution_id = await schedule_single_strategy(challenge_id, profile_id, challenge_title)
                    if execution_id:
                        scheduled_count += 1
                        print(f"✅ Strategy scheduled with execution_id: {execution_id}")
                    else:
                        print(f"⚠️ Strategy scheduling returned no execution_id")
                except Exception as e:
                    print(f"❌ Error scheduling strategy {strategy_name} for challenge {challenge_id}: {e}")
        
        print(f"📊 Total: {scheduled_count} strategies successfully scheduled across {len(challenge_strategies_by_profile)} profiles")
        
    except Exception as e:
        print(f"❌ Error in schedule_strategies_from_ini: {e}")

# Ancienne fonction supprimée due aux problèmes d'indentation
async def schedule_single_strategy(challenge_id, profile_id, challenge_title=None):
    """Programme une stratégie spécifique pour un challenge et profil donnés - utilise ExtendedStrategyExecutor"""
    try:
        print(f"🎯 Programming single strategy for challenge {challenge_id} (profile: {profile_id})")
        log_and_broadcast(
            f"🎯 Programming single strategy for challenge {challenge_id} (profile: {profile_id})",
            "strategy", profile_id)
        
        # Charger les stratégies depuis gsgui.ini
        challenge_strategies_by_profile = load_challenge_strategies()
        
        # Trouver la stratégie spécifique pour ce profil
        strategy_info = None
        if profile_id in challenge_strategies_by_profile:
            profile_strategies = challenge_strategies_by_profile[profile_id]
            if challenge_id in profile_strategies:
                strategy_info = profile_strategies[challenge_id]
        
        if not strategy_info:
            print(f"❌ No strategy found for challenge {challenge_id} and profile {profile_id}")
            return
        
        strategy_name = strategy_info['strategy_name']
        title = challenge_title or strategy_info.get('challenge_title', f'Challenge {challenge_id}')
        
        # UTILISER LE NOUVEAU SYSTÈME ExtendedStrategyExecutor
        from app.services.extended_strategy_executor import extended_strategy_executor
        
        # Utiliser le titre du challenge si disponible
        challenge_display_name = await get_challenge_title(challenge_id, profile_id)
        
        print(f"🚀 Using ExtendedStrategyExecutor for strategy '{strategy_name}' on {challenge_display_name}")
        log_and_broadcast(f"🚀 Using ExtendedStrategyExecutor for strategy '{strategy_name}' on {challenge_display_name}", "info", profile_id)
        
        # Récupérer l'URL du challenge pour les actions qui en ont besoin (comme vote)
        # Utilise exactement la même méthode que simple_vote() et fill_challenges
        challenge_url = ""
        try:
            # Récupérer le profil (comme dans simple_vote)
            profile = ProfileService.get_profile(profile_id)
            if not profile:
                print(f"⚠️ Profile {profile_id} not found")
            else:
                x_token = profile.get('xtoken')
                if x_token:
                    # Créer l'API comme dans simple_vote()
                    profile_api = create_gurushots_api(x_token)
                    if profile_api:
                        print(f"🔍 Getting challenge URL for {challenge_id} using get_challenges()")
                        challenges_data = await profile_api.get_challenges()
                        print(f"🔍 get_challenges() returned {type(challenges_data)} with {len(challenges_data) if isinstance(challenges_data, list) else 'unknown'} items")
                        
                        # challenges_data est une liste d'objets ChallengeData (comme fill_challenges)
                        if isinstance(challenges_data, list):
                            print(f"🔍 Searching for challenge {challenge_id} in {len(challenges_data)} challenges...")
                            for i, challenge_obj in enumerate(challenges_data):
                                if hasattr(challenge_obj, 'id'):
                                    if i < 5:  # Debug seulement les premiers 5
                                        print(f"  Challenge {i}: ID={challenge_obj.id}, URL={getattr(challenge_obj, 'url', 'NO_URL')}")
                                    if str(challenge_obj.id) == str(challenge_id):
                                        # Utiliser challenge_data qui contient le dict avec l'URL
                                        challenge_data = challenge_obj.challenge_data if hasattr(challenge_obj, 'challenge_data') else {'id': challenge_obj.id, 'url': getattr(challenge_obj, 'url', None)}
                                        challenge_url = challenge_data.get('url', '')
                                        print(f"✅ Found challenge {challenge_id} URL: {challenge_url}")
                                        break
                                
            if not challenge_url:
                print(f"⚠️ Could not find URL for challenge {challenge_id}")
        except Exception as e:
            print(f"⚠️ Warning: Could not get challenge URL for {challenge_id}: {e}")
            import traceback
            traceback.print_exc()
        
        # Exécuter avec le nouveau système qui gère automatiquement NOW vs FUTURE
        execution_id = await extended_strategy_executor.execute_extended_strategy(
            profile_id=profile_id,
            challenge_id=challenge_id,
            challenge_url=challenge_url,
            strategy_name=strategy_name
        )
        
        print(f"✅ Strategy '{strategy_name}' started for {challenge_display_name} with execution_id: {execution_id}")
        log_and_broadcast(f"✅ Strategy '{strategy_name}' started for {challenge_display_name}", "success", profile_id)
        
        return execution_id
        
    except Exception as e:
        print(f"❌ Error in schedule_single_strategy: {e}")
        log_and_broadcast(
            f"❌ Error in schedule_single_strategy: {e}",
            "strategy", profile_id)

def calculate_execution_time(timing_str, challenge_data=None):
    """Parse les spécifications de timing - version adaptée de parse_timing_spec"""
    try:
        from datetime import timedelta
        now = datetime.now()
        
        if timing_str == "now":
            return now
        
        elif timing_str.startswith("end-"):
            # Format: end-4m0s
            time_str = timing_str[4:]  # Retirer "end-"
            offset = parse_time_offset(time_str)
            if offset is None:
                return None
            
            # Si on a les données du challenge, calculer l'heure absolue
            if challenge_data:
                try:
                    # Essayer de récupérer l'heure de fin du challenge
                    end_time = None
                    
                    # Debug: afficher la structure du challenge
                    print(f"🔍 Challenge data keys: {list(challenge_data.keys())}")
                    
                    # Essayer d'accéder aux données originales pour le close_time
                    original_data = challenge_data.get('_original_data', challenge_data)
                    print(f"🔍 Original data keys: {list(original_data.keys())}")
                    
                    # Essayer différents champs possibles pour l'heure de fin
                    if 'close_time' in original_data:
                        close_time = original_data['close_time']
                        print(f"🕒 Found close_time: {close_time}")
                        try:
                            # Convertir le timestamp Unix en datetime puis au format GuruShots
                            end_time = datetime.fromtimestamp(close_time)
                            print(f"🕒 Parsed from timestamp: {end_time}")
                        except Exception as parse_error:
                            print(f"⚠️ Error parsing close_time '{close_time}': {parse_error}")
                    
                    elif 'end_time' in challenge_data:
                        end_time_str = challenge_data['end_time']
                        print(f"🕒 Found end_time: {end_time_str}")
                        try:
                            # Format GuruShots classique: "31/07/2025, 13:28"
                            end_time = datetime.strptime(end_time_str, "%d/%m/%Y, %H:%M")
                            print(f"🕒 Parsed classic time: {end_time}")
                        except:
                            try:
                                # Format ISO avec timezone
                                end_time = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
                                print(f"🕒 Parsed ISO time: {end_time}")
                            except Exception as parse_error:
                                print(f"⚠️ Error parsing end time '{end_time_str}': {parse_error}")
                    
                    elif 'time_left' in challenge_data:
                        time_left_data = challenge_data['time_left']
                        print(f"🕒 time_left structure: {time_left_data}")
                        if isinstance(time_left_data, dict):
                            # Calculer depuis days/hours/minutes
                            days = time_left_data.get('days', 0)
                            hours = time_left_data.get('hours', 0)  
                            minutes_left = time_left_data.get('minutes', 0)
                            # Ignorer les secondes pour arrondir à la minute supérieure
                            total_seconds_left = days * 86400 + hours * 3600 + minutes_left * 60
                            end_time_raw = datetime.now() + timedelta(seconds=total_seconds_left)
                            # Arrondir à la minute supérieure (ignorer les secondes)
                            end_time = end_time_raw.replace(second=0, microsecond=0)
                            if end_time_raw.second > 0:
                                end_time += timedelta(minutes=1)
                            print(f"🕒 Calculated end time from time_left (rounded): {end_time}")
                    
                    if end_time:
                        # Calculer le moment d'exécution: end_time - offset
                        target_time = end_time - timedelta(seconds=offset)
                        print(f"🕒 Challenge ends at: {end_time.strftime('%H:%M:%S')}")
                        print(f"🕒 Execution time (end - {offset}s): {target_time.strftime('%H:%M:%S')}")
                        return target_time
                    else:
                        print(f"⚠️ Could not determine challenge end time")
                        
                except Exception as e:
                    print(f"❌ Error parsing challenge data: {e}")
            
            # Ne pas utiliser de fallback - retourner None pour indiquer l'échec
            print(f"❌ Cannot calculate timing for {timing_str} without valid challenge data")
            return None
            
        elif timing_str.startswith("next-"):
            # Format: next-1h30m
            time_str = timing_str[5:]  # Retirer "next-"
            offset = parse_time_offset(time_str)
            if offset is None:
                return None

            # Arrondir l'heure actuelle à la minute (sans les secondes)
            now_rounded = now.replace(second=0, microsecond=0)
            target_time = now_rounded + timedelta(seconds=offset) 
            return target_time
        
        elif ":" in timing_str:
            # Format absolu: HH:MM:SS ou HH:MM
            try:
                if timing_str.count(':') == 2:
                    time_obj = datetime.strptime(timing_str, "%H:%M:%S").time()
                else:
                    time_obj = datetime.strptime(timing_str, "%H:%M").time()
                
                target_time = datetime.combine(now.date(), time_obj)
                if target_time <= now:
                    target_time += timedelta(days=1)  # Le lendemain
                
                return target_time 
            except:
                return None
        
        return None
        
    except Exception as e:
        print(f"❌ Error in calculate_execution_time: {e}")
        return None

async def parse_timing_spec(challenge, timing_spec):
    """Parse les spécifications de timing"""
    try:
        now = datetime.now()

        if timing_spec == "now":
            return now

        elif timing_spec.startswith("end-"):
            # Format: end-4m0s
            time_str = timing_spec[4:]  # Retirer "end-"
            offset = parse_time_offset(time_str)
            if offset is None:
                return None

            # Vérifier si on a des données de challenge
            if not challenge:
                print(f"❌ No challenge data available for timing 'end-' calculation")
                return None

            # Parser l'heure de fin du challenge
            if hasattr(challenge, 'end_time'):
                # Objet avec attributs
                end_time_str = challenge.end_time
            elif isinstance(challenge, dict):
                # Dictionnaire - essayer différents champs possibles
                end_time_str = challenge.get('end_time') or challenge.get('close_time')
                if isinstance(end_time_str, (int, float)):
                    # Timestamp Unix
                    end_time = datetime.fromtimestamp(end_time_str)
                    target_time = end_time - timedelta(seconds=offset)
                    return target_time
            else:
                print(f"⚠️ Format challenge non supporté: {type(challenge)}")
                return None
            
            if not end_time_str:
                print(f"⚠️ Pas d'heure de fin trouvée dans challenge")
                return None
                
            end_time = datetime.strptime(end_time_str, "%d/%m/%Y, %H:%M")
            target_time = end_time - timedelta(seconds=offset)
            return target_time

        elif timing_spec.startswith("next-"):
            # Format: next-1h30m
            time_str = timing_spec[5:]  # Retirer "next-"
            offset = parse_time_offset(time_str)
            if offset is None:
                return None

            # Arrondir l'heure actuelle à la minute (sans les secondes)
            now_rounded = now.replace(second=0, microsecond=0)
            target_time = now_rounded + timedelta(seconds=offset)
            return target_time

        elif timing_spec.startswith("at-"):
            # Format: at-01h02 (programmation à une heure absolue)
            time_str = timing_spec[3:]  # Retirer "at-"
            target_time = parse_time(time_str)
            if target_time is None:
                return None
            return target_time
        elif ":" in timing_spec:
            # Format absolu: HH:MM:SS ou HH:MM
            try:
                if timing_spec.count(':') == 2:
                    time_obj = datetime.strptime(timing_spec, "%H:%M:%S").time()
                else:
                    time_obj = datetime.strptime(timing_spec, "%H:%M").time()

                target_time = datetime.combine(now.date(), time_obj)
                if target_time <= now:
                    target_time += timedelta(days=1)  # Le lendemain

                return target_time
            except:
                return None

        return None

    except Exception as e:
        #print(f"❌ Erreur parsing timing '{timing_spec}': {e}")
        log_and_broadcast(f"❌ Erreur parsing timing '{timing_spec}': {e}")

        return None
def parse_time_offset(time_str):
    """Parse un offset de temps comme '4m0s' ou '1h30m'"""
    try:
        import re
        total_seconds = 0

        # Heures
        hours_match = re.search(r'(\d+)h', time_str)
        if hours_match:
            total_seconds += int(hours_match.group(1)) * 3600

        # Minutes
        minutes_match = re.search(r'(\d+)m', time_str)
        if minutes_match:
            total_seconds += int(minutes_match.group(1)) * 60

        # Secondes
        seconds_match = re.search(r'(\d+)s', time_str)
        if seconds_match:
            total_seconds += int(seconds_match.group(1))

        return total_seconds
    except:
        return None

def parse_time(time_str):
    """Parse un temps absolu comme '01h02' et retourne la prochaine occurrence de cette heure"""
    try:
        import re
        from datetime import datetime, timedelta
        
        # Format: XhY ou XhYm (par exemple: '01h02' ou '23h45m')
        hours_match = re.search(r'(\d{1,2})h', time_str)
        if not hours_match:
            return None
            
        hours = int(hours_match.group(1))
        if hours < 0 or hours > 23:
            return None
            
        # Minutes (optionnel, par défaut 0)
        minutes = 0
        minutes_match = re.search(r'(\d{1,2})(?:m|$)', time_str.replace(f'{hours}h', ''))
        if minutes_match:
            minutes = int(minutes_match.group(1))
            if minutes < 0 or minutes > 59:
                return None
        
        # Calculer la prochaine occurrence de cette heure
        now = datetime.now()
        target_today = now.replace(hour=hours, minute=minutes, second=0, microsecond=0)
        
        # Si l'heure est déjà passée aujourd'hui, programmer pour demain
        if target_today <= now:
            target_time = target_today + timedelta(days=1)
        else:
            target_time = target_today
            
        return target_time
        
    except Exception as e:
        logger.error(f"Erreur parsing time '{time_str}': {e}")
        return None

async def execute_strategy_vote(challenge_id, challenge_title, vote_count, profile_id):
    """Exécute un vote programmé par une stratégie"""
    try:
        # Log de démarrage très visible
        start_message = f"🚀 DÉMARRAGE EXECUTE_STRATEGY_VOTE - Challenge: {challenge_id}, Votes: {vote_count}, Profil: {profile_id}"
        print(start_message)
        log_and_broadcast(start_message, "vote_execution", profile_id)
        
        execution_message = f"🗳️ Exécution vote programmé: {vote_count} votes pour {challenge_title}"
        print(execution_message)
        log_and_broadcast(execution_message, "vote_execution", profile_id)
        
        # Récupérer le profil via le service
        profile = ProfileService.get_profile(profile_id)
        if not profile or not profile['xtoken']:
            profile_error = f"❌ Profil {profile_id} non trouvé ou token manquant"
            print(profile_error)
            log_and_broadcast(profile_error, "vote_error", profile_id)
            return
        
        # Récupérer les données du challenge via l'API (même méthode que pour fill)
        challenge_data = None
        try:
            # Récupérer les données du challenge via l'API GuruShots
            api = create_gurushots_api(profile.get('xtoken'))
            if api:
                print(f"🔍 Turbo: Calling get_challenges() for challenge {challenge_id}")
                challenges_data = await api.get_challenges()
                
                # challenges_data est une liste d'objets ChallengeData
                if isinstance(challenges_data, list):
                    # Chercher le challenge avec l'ID correspondant
                    for challenge_obj in challenges_data:
                        if hasattr(challenge_obj, 'id') and str(challenge_obj.id) == str(challenge_id):
                            # Utiliser challenge_data qui contient le dict avec l'URL
                            challenge_data = challenge_obj.challenge_data if hasattr(challenge_obj, 'challenge_data') else {'id': challenge_obj.id, 'url': getattr(challenge_obj, 'url', None)}
                            print(f"✅ Turbo: Found challenge {challenge_id} with URL: {challenge_data.get('url')}")
                            break
                    
                    if not challenge_data:
                        print(f"⚠️ Turbo: Challenge {challenge_id} not found in list of {len(challenges_data)} challenges")
            
            if not challenge_data:
                # Challenge non trouvé - soit expiré, soit erreur API
                not_found_message = f"⚠️ Challenge {challenge_id} ({challenge_title}) non trouvé dans les challenges actifs - vote annulé"
                print(not_found_message)
                log_and_broadcast(not_found_message, "vote_error", profile_id)
                return
            else:
                # Challenge trouvé - continuer avec le vote
                execution_message = f"✅ Challenge {challenge_id} ({challenge_title}) validé - exécution du vote"
                print(execution_message)
                log_and_broadcast(execution_message, "vote_execution", profile_id)

        except Exception as api_error:
            # En cas d'erreur API, continuer quand même avec le vote (ne pas bloquer)
            print(f"⚠️ Erreur validation challenge {challenge_id}: {api_error} - continue quand même")
            log_and_broadcast(f"⚠️ Erreur validation challenge {challenge_id}: {api_error} - continue quand même", "vote_execution", profile_id)
            challenge_data = {'id': challenge_id, 'url': f"https://gurushots.com/challenge/{challenge_id}"}
        
        if REAL_VOTE_AVAILABLE:
            # Exécuter le vote avec l'URL du challenge récupérée via le service
            api = create_gurushots_api(profile['xtoken'])
            if not api:
                await log_and_broadcast(f"⚠️ Could not create GuruShotsAPI for turbo", "error", profile_id)
                return {'success': False, 'message': 'GuruShotsAPI not available'}
            challenge_url = challenge_data.get('url', f"https://gurushots.com/challenge/{challenge_id}")
            
            result = await api.execute_simple_vote(challenge_url, vote_count)
            
            if result.success:
                success_message = f"✅ Vote réussi: {vote_count} votes pour {challenge_title}"
                print(success_message)
                log_and_broadcast(success_message, "vote_success", profile_id)
                
                # Déclencher un refresh automatique après vote réussi
                refresh_message = "🔄 Refresh automatique des challenges après Vote..."
                print(refresh_message)
                log_and_broadcast(refresh_message, "refresh_trigger", profile_id)
                
                # Envoyer challenge_update WebSocket pour refresh automatique
                await connection_manager.notify_challenge_update(profile_id, {
                    "action": "strategy_completed",
                    "challenge_id": challenge_id,
                    "vote_count": vote_count,
                    "strategy_type": "vote"
                })
                
                # Message de résumé comme pour Fill
                summary_message = f"✅ Stratégie terminée: 1/1 challenge - {vote_count} votes au total"
                print(summary_message)
                log_and_broadcast(summary_message, "success", profile_id)
            else:
                error_message = f"❌ Vote échoué: {result.message}"
                print(error_message)
                log_and_broadcast(error_message, "vote_error", profile_id)
                
                # Message d'échec
                error_summary = f"❌ Stratégie échouée: 0/1 challenge - {vote_count} votes manqués"
                print(error_summary)
                log_and_broadcast(error_summary, "error", profile_id)
        else:
            simulation_message = f"⚠️ Vote simulé: {vote_count} votes pour {challenge_title}"
            print(simulation_message)
            log_and_broadcast(simulation_message, "vote_simulation", profile_id)
            
            # Message de résumé pour simulation
            sim_summary = f"⚠️ Stratégie simulée: 1/1 challenge - {vote_count} votes simulés"
            print(sim_summary)
            log_and_broadcast(sim_summary, "warning", profile_id)
            
    except Exception as e:
        error_message = f"❌ Erreur exécution vote: {e}"
        print(error_message)
        log_and_broadcast(error_message, "error", profile_id)
        
        # Message d'échec pour exception
        exception_summary = f"❌ Stratégie échouée: erreur d'exécution - {vote_count} votes manqués"
        print(exception_summary)
        log_and_broadcast(exception_summary, "error", profile_id)
    
    finally:
        # Nettoyage automatique : vérifier s'il faut supprimer la stratégie après exécution
        try:
            await cleanup_completed_strategy(challenge_id, profile_id)
        except Exception as cleanup_error:
            print(f"⚠️ Erreur nettoyage stratégie: {cleanup_error}")
async def cleanup_completed_strategy(challenge_id, profile_id):
    """Nettoie une stratégie complètement exécutée"""
    try:
        # Vérifier s'il reste des jobs pour cette stratégie
        remaining_jobs = []
        if strategy_scheduler:
            jobs = strategy_scheduler.get_jobs()
            for job in jobs:
                if job.id.startswith(f'{profile_id}_{challenge_id}_'):
                    remaining_jobs.append(job.id)
        
        # Si plus de jobs en attente, supprimer la stratégie du fichier .ini
        if not remaining_jobs:
            success = remove_challenge_strategy(challenge_id, profile_id)
            if success:
                cleanup_message = f"🧹 Stratégie terminée et nettoyée pour challenge {challenge_id}"
                print(cleanup_message)
                log_and_broadcast(cleanup_message, "cleanup", profile_id)
            else:
                print(f"⚠️ Stratégie déjà nettoyée pour challenge {challenge_id}")
        else:
            print(f"📋 {len(remaining_jobs)} job(s) restant(s) pour challenge {challenge_id}")
            
    except Exception as e:
        print(f"❌ Erreur cleanup_completed_strategy: {e}")

async def cleanup_existing_strategy_for_challenge(challenge_id, profile_id):
    """Nettoie une stratégie existante pour un challenge avant d'en programmer une nouvelle"""
    try:
        # 1. Supprimer tous les jobs APScheduler pour ce challenge/profil
        jobs_removed = 0
        if strategy_scheduler:
            jobs_to_remove = []
            for job in strategy_scheduler.get_jobs():
                if job.id.startswith(f'{profile_id}_{challenge_id}_'):
                    jobs_to_remove.append(job.id)
            
            for job_id in jobs_to_remove:
                try:
                    strategy_scheduler.remove_job(job_id)
                    jobs_removed += 1
                    print(f"🗑️ Job supprimé: {job_id}")
                except Exception as job_error:
                    print(f"⚠️ Erreur suppression job {job_id}: {job_error}")
        
        # 2. Supprimer de gsgui.ini
        removed_from_ini = remove_challenge_strategy(challenge_id, profile_id)
        
        # 3. Supprimer de la mémoire
        memory_removed = 0
        strategies_to_remove = []
        for strategy_id, strategy_data in strategies.items():
            if (strategy_data.get('challenge_id') == challenge_id and 
                strategy_data.get('profile_id') == profile_id):
                strategies_to_remove.append(strategy_id)
        
        for strategy_id in strategies_to_remove:
            del strategies[strategy_id]
            memory_removed += 1
        
        if jobs_removed > 0 or removed_from_ini or memory_removed > 0:
            cleanup_message = f"🧹 Ancienne stratégie nettoyée pour challenge {challenge_id}: {jobs_removed} job(s), ini={removed_from_ini}, mémoire={memory_removed}"
            print(cleanup_message)
            log_and_broadcast(cleanup_message, "cleanup", profile_id)
        
    except Exception as e:
        print(f"❌ Erreur cleanup_existing_strategy_for_challenge: {e}")

async def cleanup_expired_strategies():
    """Version simplifiée du nettoyage des stratégies expirées"""
    try:
        print("🧹 Cleanup function temporarily simplified")
        return 0
    except Exception as e:
        print(f"❌ Error in cleanup: {e}")
        return 0

async def cleanup_expired_strategies_for_profile(profile_id: str):
    """Nettoie les stratégies expirées pour un profil spécifique"""
    print(f"🔍 DEBUG: Entrée dans cleanup_expired_strategies_for_profile avec profile_id='{profile_id}'")
    try:
        print(f"🧹 Nettoyage des stratégies expirées pour profil {profile_id}...")
        
        challenge_strategies_by_profile = load_challenge_strategies()
        print(f"🔍 DEBUG: challenge_strategies_by_profile = {challenge_strategies_by_profile}")
        if not challenge_strategies_by_profile:
            return 0
        
        cleaned_count = 0
        
        # Charger les stratégies disponibles depuis strategies.ini
        strategies_ini_path = os.path.join(os.path.dirname(__file__), "data", "strategies.ini")
        available_strategies = set()
        
        if os.path.exists(strategies_ini_path):
            with strategies_ini_lock:
                strategies_config = ConfigObj(strategies_ini_path, encoding='utf-8')
                available_strategies = set(strategies_config.keys())
                print(f"🔍 DEBUG: Stratégies disponibles: {sorted(available_strategies)}")
        
        # Obtenir les stratégies pour ce profil uniquement
        profile_strategies = challenge_strategies_by_profile.get(profile_id.lower(), {})
        print(f"🔍 DEBUG: Profils disponibles: {list(challenge_strategies_by_profile.keys())}")
        print(f"🔍 DEBUG: Recherche profil: '{profile_id.lower()}'")
        
        if not profile_strategies:
            print(f"📋 Aucune stratégie trouvée pour profil {profile_id}")
            return 0
        
        # ÉTAPE 1: Purger les stratégies inexistantes dans strategies.ini
        print(f"🔍 DEBUG: Stratégies du profil {profile_id}: {profile_strategies}")
        for challenge_id, strategy_info in list(profile_strategies.items()):
            strategy_name = strategy_info.get('strategy_name', '')
            print(f"🔍 DEBUG: Challenge {challenge_id}, stratégie '{strategy_name}', existe dans .ini: {strategy_name in available_strategies}")
            if strategy_name and strategy_name not in available_strategies:
                # Stratégie inexistante - suppression immédiate
                challenge_title = strategy_info.get('challenge_title', f'Challenge {challenge_id}')
                success = remove_challenge_strategy(challenge_id, profile_id)
                if success:
                    print(f"🗑️ Stratégie inexistante supprimée pour {profile_id}: '{strategy_name}' sur {challenge_title}")
                    cleaned_count += 1
        
        # Recharger après purge des stratégies inexistantes
        challenge_strategies_by_profile = load_challenge_strategies()
        profile_strategies = challenge_strategies_by_profile.get(profile_id.lower(), {})
        
        # ÉTAPE 2: Vérifier les challenges actifs pour ce profil
        if profile_id in profiles:
            x_token = profiles[profile_id].get('xtoken')
            if x_token:
                api = create_gurushots_api(x_token)
                if api:
                    challenges_data = await api.get_challenges()
                    
                    # Vérifier si c'est le nouveau format (avec .success) ou l'ancien (liste directe)
                    if hasattr(challenges_data, 'success') and challenges_data.success:
                        # Nouveau format avec .success et .result_data
                        challenges_list = challenges_data.result_data.get('challenges', [])
                    elif isinstance(challenges_data, list):
                        # Ancien format - liste directe d'objets ChallengeData
                        challenges_list = [
                            {'id': ch.id} for ch in challenges_data if hasattr(ch, 'id')
                        ]
                    else:
                        challenges_list = []
                    
                    active_challenge_ids = {str(ch.get('id')) for ch in challenges_list}
                    
                    for challenge_id, strategy_info in profile_strategies.items():
                        # NOUVEAU: Vérifier d'abord s'il y a des jobs actifs pour ce challenge
                        future_jobs = []
                        if strategy_scheduler:
                            for job in strategy_scheduler.get_jobs():
                                if job.id.startswith(f'{profile_id}_{challenge_id}_'):
                                    future_jobs.append(job)
                        
                        if future_jobs:
                            # Il y a encore des jobs programmés - NE PAS SUPPRIMER
                            print(f"⏰ Challenge {challenge_id} a {len(future_jobs)} job(s) programmé(s) - conservation")
                            continue
                            
                        # Seulement maintenant vérifier si le challenge n'est plus actif
                        if str(challenge_id) not in active_challenge_ids:
                            # Challenge expiré ET aucun job programmé
                            challenge_title = strategy_info.get('challenge_title', f'Challenge {challenge_id}')
                            success = remove_challenge_strategy(challenge_id, profile_id)
                            if success:
                                print(f"🗑️ Challenge expiré supprimé pour {profile_id}: {challenge_title}")
                                cleaned_count += 1
        
        print(f"✅ Profil {profile_id}: {cleaned_count} stratégie(s) expirée(s) nettoyée(s)")
        return cleaned_count
        
    except Exception as e:
        print(f"❌ Erreur cleanup profil {profile_id}: {e}")
        return 0

async def cleanup_expired_strategies_global():
    """Nettoie les stratégies expirées pour tous les profils"""
    try:
        print("🧹 Nettoyage global des stratégies expirées...")
        
        total_cleaned = 0
        for profile_id in profiles.keys():
            cleaned_count = await cleanup_expired_strategies_for_profile(profile_id)
            total_cleaned += cleaned_count
        
        print(f"✅ Cleanup global: {total_cleaned} stratégie(s) expirée(s) nettoyée(s)")
        return total_cleaned
        
    except Exception as e:
        print(f"❌ Erreur cleanup global: {e}")
        return 0

@app.get("/api/v1/debug/scheduler-status")
async def get_scheduler_status():
    """Debug endpoint pour vérifier le statut du scheduler"""
    try:
        if strategy_scheduler:
            jobs = strategy_scheduler.get_jobs()
            job_info = []
            for job in jobs:
                job_info.append({
                    "id": job.id,
                    "next_run": str(job.next_run_time),
                    "function": job.func.__name__ if job.func else None,
                    "args": list(job.args),
                })
            
            return {
                "scheduler_running": strategy_scheduler.running,
                "job_count": len(jobs),
                "jobs": job_info
            }
        else:
            return {"error": "Scheduler not initialized"}
    except Exception as e:
        return {"error": str(e)}

def load_profiles_from_ini():
    """Charge les profils depuis gsgui.ini au démarrage"""
    global profiles
    try:
        # Utiliser le service pour charger les profils
        profiles = ProfileService.get_all_profiles()
        
        for profile_name in profiles.keys():
            print(f"✅ Profil {profile_name} chargé depuis .ini")
        
        print(f"📋 {len(profiles)} profil(s) chargé(s)")
    except Exception as e:
        print(f"❌ Erreur chargement profils: {e}")

@app.on_event("startup")
async def startup_event():
    """Événements de démarrage du backend"""
    global gurushots_api, strategy_scheduler
    
    logger.info("🚀 Backend startup - Loading strategies and turbo states...")
    
    # Charger les profils depuis .ini
    load_profiles_from_ini()
    
    # NOTE: Les stratégies sont programmées dans startup_event() après l'init du scheduler
    
    # Nettoyer les stratégies expirées au démarrage
    await cleanup_expired_strategies()
    
    # Charger les états turbo existants
    # Plus de chargement des états turbo - calcul dynamique uniquement
    logger.info("📋 Turbo states calculated dynamically from API data")
    
    # Initialiser le service GuruShots avec le token depuis la config
    if REAL_VOTE_AVAILABLE:
        try:
            user_token = get_user_token_from_config()
            if user_token:
                gurushots_api = create_gurushots_api(user_token)
                if not gurushots_api:
                    logger.warning("⚠️ Could not create GuruShotsAPI for profile loading")
                    return
                logger.info("✅ GuruShots API service initialized with real voting capability")
            else:
                logger.warning("⚠️ No user token found in config - using simulated voting")
        except Exception as e:
            logger.error(f"❌ Failed to initialize GuruShots API service: {e}")
            logger.warning("⚠️ Falling back to simulated voting")
    
    # Initialiser le service StrategyScheduler (instance unique)
    try:
        if STRATEGY_SCHEDULER_AVAILABLE:
            from app.services.strategy_scheduler import strategy_scheduler
            await strategy_scheduler.start()

            # Programmer les stratégies existantes
            logger.info("🔄 Starting strategy scheduling from .ini...")
            await schedule_strategies_from_ini()
            logger.info("✅ StrategyScheduler service initialized")

            # Initialiser le service AutoRefreshScheduler
            try:
                from app.services.auto_refresh_scheduler import init_auto_refresh_scheduler
                auto_refresh_sched = init_auto_refresh_scheduler(strategy_scheduler)

                # Restaurer les auto-refresh depuis la config
                await auto_refresh_sched.restore_from_config()
                logger.info("✅ AutoRefreshScheduler service initialized")
            except Exception as e:
                logger.error(f"❌ Failed to initialize AutoRefreshScheduler: {e}")
                logger.warning("⚠️ Auto-refresh feature will not be available")
        else:
            logger.warning("⚠️ StrategyScheduler service not available")
    except Exception as e:
        logger.error(f"❌ Failed to initialize StrategyScheduler service: {e}")
        logger.warning("⚠️ Strategies will be stored but not automatically executed")

if __name__ == "__main__":
    # Configuration du logging avant démarrage
    import logging.handlers
    
    # Setup logging rotatif
    log_dir = "../logs"
    os.makedirs(log_dir, exist_ok=True)
    
    # Configuration du logger racine
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Supprimer les handlers existants
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Handler rotatif pour backend.log
    backend_handler = logging.handlers.RotatingFileHandler(
        filename=os.path.join(log_dir, "backend.log"),
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
        encoding='utf-8'
    )
    backend_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    
    # Handler console
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    ))
    
    # Ajouter les handlers
    root_logger.addHandler(backend_handler)
    root_logger.addHandler(console_handler)
    
    logger.info("🚀 Démarrage du backend GSGUI avec vrais challenges...")
    uvicorn.run(app, host="127.0.0.1", port=8001, log_level="info")