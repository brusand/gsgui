#!/usr/bin/env python3
"""
Backend API avec vrais challenges GuruShots
"""

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
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
from app.websockets.connection_manager import connection_manager

# Imports locaux maintenant que le fichier est dans backend/
try:
    from app.services.gurushots_api import GuruShotsAPI
    REAL_VOTE_AVAILABLE = True
    print("✅ GuruShotsAPI imported successfully")
except ImportError as e:
    print(f"⚠️ GuruShotsAPI import failed: {e}")
    REAL_VOTE_AVAILABLE = False

try:
    from app.services.strategy_scheduler import StrategyScheduler
    STRATEGY_SCHEDULER_AVAILABLE = True
    print("✅ StrategyScheduler imported successfully")
except ImportError as e:
    print(f"⚠️ Strategy Scheduler service not available: {e}")
    STRATEGY_SCHEDULER_AVAILABLE = False

# Helper function pour créer GuruShotsAPI
def create_gurushots_api(token):
    """Crée une instance GuruShotsAPI"""
    try:
        return GuruShotsAPI(token)
    except Exception as e:
        print(f"⚠️ Error creating GuruShotsAPI: {e}")
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
                config = ConfigObj('./data/gsgui.ini', encoding='utf-8')
                
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
                config = ConfigObj('./data/gsgui.ini', encoding='utf-8')
                
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
            
            real_challenges = await fetch_real_challenges(profile['xtoken'])
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
                    real_challenges = await fetch_real_challenges(x_token)
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
    """Log local + diffusion WebSocket (version synchrone)"""
    print(message)
    # Créer une tâche asynchrone pour la diffusion
    try:
        # Diffuser aux WebSockets par profil
        if profile_name:
            asyncio.create_task(connection_manager.notify_broadcast_log(
                profile_name, log_type, message))
        asyncio.create_task(broadcast_log(message, log_type, profile_name))
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

async def fetch_real_challenges(xtoken: str) -> List[Dict[str, Any]]:
    """Récupère les vrais challenges depuis l'API GuruShots"""
    try:
        headers = get_aio_headers(xtoken)
        print(f"🔍 Fetching real challenges avec token: {xtoken[:20]}...")
        
        connector = aiohttp.TCPConnector(ssl=False)
        async with aiohttp.ClientSession(headers=headers, connector=connector) as session:
            async with session.post('https://api.gurushots.com/rest/get_my_active_challenges') as response:
                print(f"📡 GuruShots API status: {response.status}")
                
                if response.status != 200:
                    print(f"❌ API Error: Status {response.status}")
                    return []
                
                data = await response.json()
                print(f"📊 API data keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                
                # Debug : si success=false, afficher l'erreur
                if isinstance(data, dict) and not data.get('success', True):
                    error_code = data.get('error_code', 'unknown')
                    error_msg = data.get('error', 'No error message')
                    print(f"❌ GuruShots API Error: {error_code} - {error_msg}")
                    print(f"🔍 Full response: {data}")
                
                challenges = []
                for challenge_data in data.get('challenges', []):
                    try:
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
                
                # Trier par temps restant croissant (comme gs_backend_ui.py)
                challenges.sort(key=lambda x: x['time_left_seconds'])
                print(f"✅ Successfully processed {len(challenges)} real challenges (triés par temps restant)")
                return challenges
                
    except Exception as e:
        print(f"❌ Error fetching real challenges: {e}")
        import traceback
        traceback.print_exc()
        return []

def load_challenge_strategies():
    """Charge les stratégies stockées depuis gsgui.ini organisées par profil"""
    try:
        with gsgui_ini_lock:
            config = ConfigObj('./data/gsgui.ini', encoding='utf-8')
            challenge_strategies_by_profile = {}
            
            if 'players' not in config:
                return {}
            
            # Parcourir tous les profils
            for profile_id, profile_data in config['players'].items():
                if isinstance(profile_data, dict) and 'scheduled_strategies' in profile_data:
                    profile_strategies = {}
                    for challenge_id, strategy_data in profile_data['scheduled_strategies'].items():
                        if isinstance(strategy_data, dict):
                            profile_strategies[challenge_id] = {
                                'strategy_name': strategy_data.get('strategy_name', ''),
                                'scheduled_at': strategy_data.get('scheduled_at', ''),
                                'challenge_title': strategy_data.get('challenge_title', f'Challenge {challenge_id}'),
                                'status': 'pending',
                                'profile_id': profile_id
                            }
                    
                    if profile_strategies:
                        challenge_strategies_by_profile[profile_id] = profile_strategies
            
            total_strategies = sum(len(strategies) for strategies in challenge_strategies_by_profile.values())
            print(f"📋 Loaded {total_strategies} challenge strategies from gsgui.ini across {len(challenge_strategies_by_profile)} profiles")
            return challenge_strategies_by_profile
    except Exception as e:
        print(f"❌ Error loading challenge strategies: {e}")
        return {}

def save_challenge_strategy(challenge_id: str, strategy_name: str, scheduled_at: str, profile_id: str = "bruno", challenge_title: str = None):
    """Sauvegarde une stratégie pour un challenge dans gsgui.ini sous le profil"""
    try:
        with gsgui_ini_lock:
            config = ConfigObj('./data/gsgui.ini', encoding='utf-8')
            
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
                'challenge_title': challenge_title or f"Challenge {challenge_id}",
                'scheduled_at': scheduled_at
            }
            
            config.write()
            display_name = challenge_title if challenge_title else f"Challenge {challenge_id}"
            log_and_broadcast(f"💾 Saved strategy {strategy_name} for {display_name}", "success", profile_id)
            return True
    except Exception as e:
        error_msg = f"❌ Error saving challenge strategy: {e}"
        log_and_broadcast(error_msg, "error", profile_id)
        return False

def remove_challenge_strategy(challenge_id: str, profile_id: str = None):
    """Supprime une stratégie d'un challenge depuis gsgui.ini pour un profil donné"""
    try:
        with gsgui_ini_lock:
            config = ConfigObj('./data/gsgui.ini', encoding='utf-8')
            
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
        turbo_status = challenge_data['member']['turbo']
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

def get_user_token_from_config() -> Optional[str]:
    """Récupère le token depuis la config"""
    try:
        with gsgui_ini_lock:
            config = ConfigObj('./data/gsgui.ini', encoding='utf-8')
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
                config = ConfigObj('./data/gsgui.ini', encoding='utf-8')
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
                    config = ConfigObj('./data/gsgui.ini', encoding='utf-8')
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
        real_challenges = await fetch_real_challenges(x_token)
        
        if not real_challenges:
            print("⚠️ No real challenges, using config token...")
            # Fallback: essayer avec le token de la config
            config_token = get_user_token_from_config()
            if config_token:
                real_challenges = await fetch_real_challenges(config_token)
        
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
                challenge['strategy_status'] = strategy_info['status']
            else:
                challenge['selected_strategy'] = None
                challenge['strategy_status'] = None
            
            # États turbo intelligents avec données originales
            original_data = challenge.get('_original_data', {})
            challenge['turbo_status'] = determine_turbo_status(challenge, original_data)
            
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
            display_name = request.challenge_title if request.challenge_title else f"challenge {request.challenge_id}"
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
                        # Format: "vote, end-4m0s, 70" ou "end-4m0s, 70"
                        if len(parts) == 3:
                            action_type = parts[0]
                            timing = parts[1]
                            vote_count_str = parts[2]
                        elif len(parts) == 2:
                            action_type = 'vote'
                            timing = parts[0]
                            vote_count_str = parts[1]
                        else:
                            continue
                        
                        try:
                            vote_count = int(vote_count_str)
                            # Ignorer les votes négatifs (-1) qui indiquent "pas de vote"
                            if vote_count > 0:
                                actions.append({
                                    'action': action_type,
                                    'timing': timing,
                                    'votes': vote_count,
                                    'raw': clean_value
                                })
                        except ValueError:
                            print(f"⚠️ Invalid vote count in strategy {strategy_name}: {vote_count_str}")
                            continue
            
            return actions
    except Exception as e:
        print(f"❌ Error parsing strategy {strategy_name}: {e}")
        return []










@app.get("/api/v1/strategies/active")
async def get_active_strategies(profile_name: Optional[str] = None):
    """Récupère les stratégies actives avec détails et noms des challenges"""
    try:
        challenge_strategies_by_profile = load_challenge_strategies()
        
        if not challenge_strategies_by_profile:
            return {"strategies": [], "total_count": 0, "total_jobs": 0}
        
        # Récupérer les challenges pour avoir les vrais noms
        challenges_map = {}
        if profile_name:
            try:
                # Récupérer le token depuis le profil
                profile_id = profile_name.lower()
                if profile_id in profiles:
                    x_token = profiles[profile_id].get('xtoken')
                    if x_token:
                        real_challenges = await fetch_real_challenges(x_token)
                        challenges_map = {ch['id']: ch['title'] for ch in real_challenges}
                        print(f"✅ Mapping {len(challenges_map)} challenge titles for strategies")
            except Exception as e:
                print(f"⚠️ Could not fetch challenge titles: {e}")
        
        detailed_strategies = []
        total_jobs = 0
        
        # Parcourir les profils et leurs stratégies
        for current_profile_id, profile_strategies in challenge_strategies_by_profile.items():
            # Filtrer par profil si spécifié
            if profile_name:
                profile_id = profile_name.lower()
                if current_profile_id != profile_id:
                    continue  # Ignorer les stratégies des autres profils
            
            for challenge_id, strategy_info in profile_strategies.items():
                strategy_name = strategy_info['strategy_name']
                
                # Parser les actions de la stratégie
                actions = parse_strategy_actions(strategy_name)
                total_jobs += len(actions)
                
                # Récupérer le vrai nom du challenge
                challenge_title = challenges_map.get(challenge_id, f"Challenge {challenge_id}")
                
                # Récupérer les données du challenge pour calculer les heures d'exécution
                challenge_data = None
                if profile_name:
                    profile_id = profile_name.lower()
                    try:
                        if profile_id in profiles:
                            x_token = profiles[profile_id].get('xtoken')
                            if x_token:
                                real_challenges = await fetch_real_challenges(x_token)
                                # Chercher le challenge dans la liste
                                for challenge in real_challenges:
                                    if str(challenge.get('id')) == str(challenge_id):
                                        challenge_data = challenge
                                        print(f"🔍 Found challenge data for {challenge_id}: {challenge.get('title', 'N/A')}")
                                        break
                    except Exception as e:
                        print(f"⚠️ Could not fetch challenge data for {challenge_id}: {e}")
                
                # Calculer les heures d'exécution absolues pour chaque action
                actions_with_execution_times = []
                for action in actions:
                    execution_time =  calculate_execution_time(action['timing'], challenge_data) #await parse_timing_spec(challenge_data, action['timing'])#calculate_execution_time(action['timing'], challenge_data)
                    action_with_time = action.copy()
                    if execution_time:
                        action_with_time['execution_time'] = execution_time.strftime('%H:%M:%S')
                        action_with_time['execution_datetime'] = execution_time.isoformat()

                    actions_with_execution_times.append(action_with_time)
                
                detailed_strategies.append({
                    'challenge_id': challenge_id,
                    'challenge_title': challenge_title,
                    'strategy_name': strategy_name,
                    'status': strategy_info['status'],
                    'scheduled_at': strategy_info['scheduled_at'],
                    'actions': actions_with_execution_times
                })
        
        return {
            "strategies": detailed_strategies,
            "total_count": len(detailed_strategies),
            "total_jobs": total_jobs
        }
        
    except Exception as e:
        print(f"❌ Error getting active strategies: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/profiles")
async def get_profiles():
    """Récupère la liste des profils depuis gsgui.ini"""
    try:
        with gsgui_ini_lock:
            gsgui_ini_path = "./data/gsgui.ini"
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
            gsgui_ini_path = "./data/gsgui.ini"
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
            print(f"🎯 Processing {len(profile_strategies)} strategies for profile {profile_id}")
            for challenge_id, strategy_info in profile_strategies.items():
                strategy_name = strategy_info['strategy_name']
                print(f"  - Challenge {challenge_id}: strategy {strategy_name}")
                scheduled_count += 1
        
        print(f"📊 Total: {scheduled_count} strategies found across {len(challenge_strategies_by_profile)} profiles")
        
    except Exception as e:
        print(f"❌ Error in schedule_strategies_from_ini: {e}")

# Ancienne fonction supprimée due aux problèmes d'indentation
async def schedule_single_strategy(challenge_id, profile_id, challenge_title=None):
    """Programme une stratégie spécifique pour un challenge et profil donnés"""
    try:
        global strategy_scheduler
        
        if not strategy_scheduler:
            print("❌ Strategy scheduler not initialized")
            return
        
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
        
        print(f"🎯 {title}:")
        
        # Parser les actions de la stratégie
        actions = parse_strategy_actions(strategy_name)
        
        if not actions:
            print(f"   ⚠️ Aucune action définie pour stratégie {strategy_name}")
            return
        
        # Récupérer les données du challenge via le service
        challenge_data = await ChallengeService.get_challenge_data(challenge_id, profile_id)
        if challenge_data:
            print(f"🔍 Found challenge data for {challenge_id}: {challenge_data.get('title', 'N/A')}")
        else:
            print(f"⚠️ Could not fetch challenge data for {challenge_id}")
        
        scheduled_count = 0
        
        # Programmer chaque action
        for action in actions:
            execution_time = calculate_execution_time(action['timing'], challenge_data)
            
            if execution_time is None:
                print(f"   ❌ Impossible de calculer le timing pour {action['timing']} - action ignorée")
                continue
            
            #if execution_time <= datetime.now():
            #    print(f"   ⚠️ Action {action['timing']} dans le passé - action ignorée")
            #    continue

            if 'vote' in action['action']:
                # Programmer le job avec APScheduler
                if 'now' in action['timing']:
                    job_id = f"{profile_id}_{challenge_id}_{action['timing']}_{action['votes']}"
                    strategy_scheduler.add_job(
                        execute_strategy_vote,
                        'date',
                        args=[challenge_id, title, action['votes'], profile_id],
                        id=job_id,
                        replace_existing=True
                    )
                    print(f"📅 JOB IMMÉDIAT PROGRAMMÉ: {job_id} - ARGS: {[challenge_id, title, action['votes'], profile_id]}")
                    log_and_broadcast(f"📅 Job APScheduler immédiat programmé: {job_id}", "strategy", profile_id)
                else:
                    job_id = f"{profile_id}_{challenge_id}_{action['timing']}_{action['votes']}"
                    strategy_scheduler.add_job(
                        execute_strategy_vote,
                        'date',
                        run_date=execution_time,
                        args=[challenge_id, title, action['votes'], profile_id],
                        id=job_id,
                        replace_existing=True
                    )
                
                # Affichage avec l'heure absolue calculée
                formatted_time = execution_time.strftime('%H:%M:%S')
                print(f"   ⏰ Programmé: vote {action['votes']} à {formatted_time} pour {title}")
                log_and_broadcast(
                    f"   ⏰ Programmé: vote {action['votes']} à {formatted_time} pour {title}",
                    "strategy", profile_id)
                scheduled_count += 1
        
        print(f"📊 Challenge {challenge_id}: {scheduled_count} job(s) programmé(s)")
        log_and_broadcast(
            f"📊 Challenge {challenge_id}: {scheduled_count} job(s) programmé(s)",
            "strategy", profile_id)
        
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
    try:
        print(f"🧹 Nettoyage des stratégies expirées pour profil {profile_id}...")
        
        challenge_strategies_by_profile = load_challenge_strategies()
        if not challenge_strategies_by_profile:
            return 0
        
        cleaned_count = 0
        
        # Obtenir les stratégies pour ce profil uniquement
        profile_strategies = challenge_strategies_by_profile.get(profile_id.lower(), {})
        
        if not profile_strategies:
            print(f"📋 Aucune stratégie trouvée pour profil {profile_id}")
            return 0
        
        # Vérifier les challenges actifs pour ce profil
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
                        if str(challenge_id) not in active_challenge_ids:
                            # Challenge expiré
                            challenge_title = strategy_info.get('challenge_title', f'Challenge {challenge_id}')
                            success = remove_challenge_strategy(challenge_id, profile_id)
                            if success:
                                print(f"🗑️ Challenge expiré supprimé pour {profile_id}: {challenge_title}")
                                cleaned_count += 1
                            
                            # Supprimer les jobs du scheduler
                            if strategy_scheduler:
                                jobs_to_remove = []
                                for job in strategy_scheduler.get_jobs():
                                    if job.id.startswith(f'{profile_id}_{challenge_id}_'):
                                        jobs_to_remove.append(job.id)
                                
                                for job_id in jobs_to_remove:
                                    try:
                                        strategy_scheduler.remove_job(job_id)
                                        print(f"  🗑️ Job {job_id} supprimé du scheduler")
                                    except Exception as job_error:
                                        print(f"  ⚠️ Erreur suppression job {job_id}: {job_error}")
        
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
    
    print("🚀 Backend startup - Loading strategies and turbo states...")
    
    # Charger les profils depuis .ini
    load_profiles_from_ini()
    
    # NOTE: Les stratégies sont programmées dans startup_event() après l'init du scheduler
    
    # Nettoyer les stratégies expirées au démarrage
    await cleanup_expired_strategies()
    
    # Charger les états turbo existants
    # Plus de chargement des états turbo - calcul dynamique uniquement
    print("📋 Turbo states calculated dynamically from API data")
    
    # Initialiser le service GuruShots avec le token depuis la config
    if REAL_VOTE_AVAILABLE:
        try:
            user_token = get_user_token_from_config()
            if user_token:
                gurushots_api = create_gurushots_api(user_token)
                if not gurushots_api:
                    print(f"⚠️ Could not create GuruShotsAPI for profile loading")
                    return
                print("✅ GuruShots API service initialized with real voting capability")
            else:
                print("⚠️ No user token found in config - using simulated voting")
        except Exception as e:
            print(f"❌ Failed to initialize GuruShots API service: {e}")
            print("⚠️ Falling back to simulated voting")
    
    # Initialiser notre propre système d'exécution de stratégies
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        strategy_scheduler = AsyncIOScheduler()
        strategy_scheduler.start()
        
        # Programmer les stratégies existantes
        print("🔄 Starting strategy scheduling from .ini...")
        await schedule_strategies_from_ini()
        print("✅ Custom Strategy Scheduler initialized with challenge titles support")
    except Exception as e:
        print(f"❌ Failed to initialize Custom Strategy Scheduler: {e}")
        print("⚠️ Strategies will be stored but not automatically executed")

if __name__ == "__main__":
    print("🚀 Démarrage du backend GSGUI avec vrais challenges...")
    uvicorn.run(app, host="127.0.0.1", port=8001, log_level="info")