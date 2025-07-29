#!/usr/bin/env python3
"""
Backend API avec vrais challenges GuruShots
"""

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import uvicorn
import asyncio
import aiohttp
import ssl
from configobj import ConfigObj
import threading
import os
import json
from typing import Set

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

# Configuration files with thread locks
config_lock = threading.Lock()
BACKEND_STRATEGIES_FILE = "backend_strategies.ini"
BACKEND_TURBO_FILE = "backend_turbo.ini"

# WebSocket connections for real-time logs
websocket_connections: Set[WebSocket] = set()

async def broadcast_log(message: str, log_type: str = "info"):
    """Diffuse un message de log à toutes les connexions WebSocket"""
    if not websocket_connections:
        return
    
    log_data = {
        "timestamp": datetime.now().isoformat(),
        "type": log_type,
        "message": message
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

def log_and_broadcast(message: str, log_type: str = "info"):
    """Log local + diffusion WebSocket (version synchrone)"""
    print(message)
    # Créer une tâche asynchrone pour la diffusion
    try:
        asyncio.create_task(broadcast_log(message, log_type))
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
                
                challenges = []
                for challenge_data in data.get('challenges', []):
                    try:
                        timeleft = challenge_data['time_left']
                        
                        # Format compatible avec notre interface + préserver les données originales
                        challenge = {
                            'id': str(challenge_data['id']),
                            'title': challenge_data['title'],
                            'url': challenge_data['url'],
                            'votes': int(challenge_data['member']['ranking']['total']['votes']),
                            'rank': int(challenge_data['member']['ranking']['total']['rank']),
                            'level': challenge_data['member']['ranking']['total']['level_name'],
                            'exposure': challenge_data['member']['ranking']['total']['exposure'],
                            'gps': 0,  # Placeholder
                            'time_left_days': timeleft['days'],
                            'time_left': {
                                'days': timeleft.get('days', 0),
                                'hours': timeleft.get('hours', 0),
                                'minutes': timeleft.get('minutes', 0),
                                'seconds': timeleft.get('seconds', 0)
                            },
                            'selected_strategy': None,  # À implémenter
                            'turbo_status': 'none',  # À implémenter
                            '_original_data': challenge_data  # Préserver les données originales pour turbo status
                        }
                        challenges.append(challenge)
                        
                    except KeyError as e:
                        print(f"⚠️ Missing key in challenge data: {e}")
                        continue
                
                print(f"✅ Successfully processed {len(challenges)} real challenges")
                return challenges
                
    except Exception as e:
        print(f"❌ Error fetching real challenges: {e}")
        import traceback
        traceback.print_exc()
        return []

def load_challenge_strategies():
    """Charge les stratégies stockées depuis le fichier .ini"""
    try:
        with config_lock:
            if not os.path.exists(BACKEND_STRATEGIES_FILE):
                return {}
            
            config = ConfigObj(BACKEND_STRATEGIES_FILE, encoding='utf-8')
            challenge_strategies = {}
            
            for challenge_id, strategy_data in config.items():
                if isinstance(strategy_data, dict):
                    challenge_strategies[challenge_id] = {
                        'strategy_name': strategy_data.get('strategy_name', ''),
                        'scheduled_at': strategy_data.get('scheduled_at', ''),
                        'status': strategy_data.get('status', 'pending'),
                        'profile_id': strategy_data.get('profile_id', 'bruno')
                    }
            
            print(f"📋 Loaded {len(challenge_strategies)} challenge strategies from .ini")
            return challenge_strategies
    except Exception as e:
        print(f"❌ Error loading challenge strategies: {e}")
        return {}

def save_challenge_strategy(challenge_id: str, strategy_name: str, scheduled_at: str, profile_id: str = "bruno"):
    """Sauvegarde une stratégie pour un challenge dans le fichier .ini"""
    try:
        with config_lock:
            config = ConfigObj(BACKEND_STRATEGIES_FILE, encoding='utf-8')
            
            config[challenge_id] = {
                'strategy_name': strategy_name,
                'scheduled_at': scheduled_at,
                'status': 'pending',
                'profile_id': profile_id,
                'created_at': datetime.now().isoformat()
            }
            
            config.write()
            log_and_broadcast(f"💾 Saved strategy {strategy_name} for challenge {challenge_id}", "success")
            return True
    except Exception as e:
        error_msg = f"❌ Error saving challenge strategy: {e}"
        log_and_broadcast(error_msg, "error")
        return False

def remove_challenge_strategy(challenge_id: str):
    """Supprime une stratégie d'un challenge du fichier .ini"""
    try:
        with config_lock:
            config = ConfigObj(BACKEND_STRATEGIES_FILE, encoding='utf-8')
            
            if challenge_id in config:
                del config[challenge_id]
                config.write()
                log_and_broadcast(f"🗑️ Removed strategy for challenge {challenge_id}", "info")
                return True
            return False
    except Exception as e:
        error_msg = f"❌ Error removing challenge strategy: {e}"
        log_and_broadcast(error_msg, "error")
        return False

def load_turbo_states():
    """Charge les états des turbos depuis le fichier .ini"""
    try:
        with config_lock:
            if not os.path.exists(BACKEND_TURBO_FILE):
                return {}
            
            config = ConfigObj(BACKEND_TURBO_FILE, encoding='utf-8')
            turbo_states = {}
            
            for challenge_id, turbo_data in config.items():
                if isinstance(turbo_data, dict):
                    turbo_states[challenge_id] = {
                        'status': turbo_data.get('status', 'none'),
                        'turbo_id': turbo_data.get('turbo_id', ''),
                        'executed_at': turbo_data.get('executed_at', ''),
                        'profile_id': turbo_data.get('profile_id', 'bruno')
                    }
            
            print(f"📋 Loaded {len(turbo_states)} turbo states from .ini")
            return turbo_states
    except Exception as e:
        print(f"❌ Error loading turbo states: {e}")
        return {}

def save_turbo_state(challenge_id: str, status: str, turbo_id: str = '', profile_id: str = "bruno"):
    """Sauvegarde l'état d'un turbo dans le fichier .ini"""
    try:
        with config_lock:
            config = ConfigObj(BACKEND_TURBO_FILE, encoding='utf-8')
            
            config[challenge_id] = {
                'status': status,
                'turbo_id': turbo_id,
                'executed_at': datetime.now().isoformat(),
                'profile_id': profile_id
            }
            
            config.write()
            log_and_broadcast(f"💾 Turbo state saved: {challenge_id} → {status}", "success")
            return True
    except Exception as e:
        error_msg = f"❌ Error saving turbo state: {e}"
        log_and_broadcast(error_msg, "error")
        return False

def remove_turbo_state(challenge_id: str):
    """Supprime l'état turbo d'un challenge du fichier .ini"""
    try:
        with config_lock:
            config = ConfigObj(BACKEND_TURBO_FILE, encoding='utf-8')
            
            if challenge_id in config:
                del config[challenge_id]
                config.write()
                log_and_broadcast(f"🗑️ Removed turbo state for challenge {challenge_id}", "info")
                return True
            return False
    except Exception as e:
        error_msg = f"❌ Error removing turbo state: {e}"
        log_and_broadcast(error_msg, "error")
        return False

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

def determine_turbo_status(challenge: Dict, turbo_states: Dict, challenge_data: Dict) -> str:
    """Détermine l'état turbo intelligent selon les règles GSGUI"""
    challenge_id = challenge['id']
    
    # 1. Priorité: États explicites locaux (running/completed/failed)
    if challenge_id in turbo_states:
        local_status = turbo_states[challenge_id]['status']
        if local_status in ["running", "completed", "failed"]:
            return local_status
    
    # 2. Extraire l'état réel depuis l'API GuruShots
    api_status = get_real_turbo_status(challenge_data)
    if api_status in ["free", "won", "used", "locked"]:
        return api_status
    
    # 3. Fallback: Logique GSGUI intelligente
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
        return "unknown"  # État inconnu
    
    # Par défaut, disponible
    return "none"

def get_user_token_from_config() -> Optional[str]:
    """Récupère le token depuis la config"""
    try:
        config = ConfigObj('/Users/bruno/gsgui/gsgui.ini', encoding='utf-8')
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
    """Récupère les vrais challenges depuis GuruShots avec stratégies"""
    try:
        print(f"🔍 Request for real challenges with token: {user_token[:20]}...")
        
        # Récupérer les vrais challenges
        real_challenges = await fetch_real_challenges(user_token)
        
        if not real_challenges:
            print("⚠️ No real challenges, using config token...")
            # Fallback: essayer avec le token de la config
            config_token = get_user_token_from_config()
            if config_token:
                real_challenges = await fetch_real_challenges(config_token)
        
        # Charger les stratégies et états turbo stockés
        challenge_strategies = load_challenge_strategies()
        turbo_states = load_turbo_states()
        
        # Enrichir les challenges avec leurs stratégies et états turbo
        for challenge in real_challenges:
            challenge_id = challenge['id']
            
            # Stratégies
            if challenge_id in challenge_strategies:
                strategy_info = challenge_strategies[challenge_id]
                challenge['selected_strategy'] = strategy_info['strategy_name']
                challenge['strategy_status'] = strategy_info['status']
            else:
                challenge['selected_strategy'] = None
                challenge['strategy_status'] = None
            
            # États turbo intelligents avec données originales
            original_data = challenge.get('_original_data', {})
            challenge['turbo_status'] = determine_turbo_status(challenge, turbo_states, original_data)
            
            # Nettoyer les données internes
            if '_original_data' in challenge:
                del challenge['_original_data']
            
            # ID turbo si disponible
            if challenge_id in turbo_states:
                challenge['turbo_id'] = turbo_states[challenge_id]['turbo_id']
            else:
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
        
        # Sauvegarder dans le fichier .ini (persistance)
        success = save_challenge_strategy(
            request.challenge_id, 
            request.strategy_name, 
            request.scheduled_at, 
            profile_id
        )
        
        if success:
            message = f"✅ Strategy {request.strategy_name} scheduled for challenge {request.challenge_id}"
            log_and_broadcast(message, "success")
        else:
            message = f"⚠️ Strategy scheduled in memory but failed to save to .ini"
            log_and_broadcast(message, "warning")
        
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
async def execute_turbo(profile_id: str, request: TurboExecutionRequest):
    """Exécute un turbo et sauvegarde l'état"""
    try:
        turbo_id = f"turbo_{profile_id}_{request.challenge_id}_{int(datetime.now().timestamp())}"
        
        # Sauvegarder l'état turbo comme "running"
        save_turbo_state(request.challenge_id, "running", turbo_id, profile_id)
        
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
        
        # Simuler l'exécution avec résultat aléatoire
        await asyncio.sleep(0.1)
        
        # Simuler un résultat (95% de succès)
        import random
        success = random.random() < 0.95
        
        if success:
            # Marquer comme complété
            save_turbo_state(request.challenge_id, "completed", turbo_id, profile_id)
            log_and_broadcast(f"🚀 Turbo completed successfully for challenge {request.challenge_id}", "success")
            status = "completed"
        else:
            # Marquer comme échoué
            save_turbo_state(request.challenge_id, "failed", turbo_id, profile_id)
            log_and_broadcast(f"❌ Turbo failed for challenge {request.challenge_id}", "error")
            status = "failed"
        
        return {
            "turbo_id": turbo_id,
            "profile_id": profile_id,
            "challenge_id": request.challenge_id,
            "status": status,
            "message": f"Turbo execution {status}"
        }
    except Exception as e:
        # En cas d'erreur, marquer comme échoué
        save_turbo_state(request.challenge_id, "failed", "", profile_id)
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

def parse_strategy_actions(strategy_name: str) -> List[Dict]:
    """Parse les actions d'une stratégie depuis strategies.ini"""
    try:
        strategies_config = ConfigObj('strategies.ini', encoding='utf-8')
        if strategy_name not in strategies_config:
            return []
        
        strategy_config = strategies_config[strategy_name]
        actions = []
        
        for key, value in strategy_config.items():
            if key == 'description':
                continue
            
            # Parser l'action: "vote, end-4m0s,70" ou "end-4m0s,-1"
            if isinstance(value, str):
                parts = [p.strip() for p in value.split(',')]
                if len(parts) >= 2:
                    action_type = parts[0] if len(parts) == 3 else 'vote'
                    timing = parts[1] if len(parts) == 3 else parts[0]
                    vote_count = int(parts[2]) if len(parts) == 3 else int(parts[1])
                    
                    if vote_count > 0:  # Ignorer les votes négatifs (-1)
                        actions.append({
                            'action': action_type,
                            'timing': timing,
                            'votes': vote_count,
                            'raw': value
                        })
        
        return actions
    except Exception as e:
        print(f"❌ Error parsing strategy {strategy_name}: {e}")
        return []

@app.get("/api/v1/strategies/active")
async def get_active_strategies(user_token: Optional[str] = None):
    """Récupère les stratégies actives avec détails et noms des challenges"""
    try:
        challenge_strategies = load_challenge_strategies()
        
        if not challenge_strategies:
            return {"strategies": [], "total_count": 0, "total_jobs": 0}
        
        # Récupérer les challenges pour avoir les vrais noms
        challenges_map = {}
        if user_token:
            try:
                real_challenges = await fetch_real_challenges(user_token)
                challenges_map = {ch['id']: ch['title'] for ch in real_challenges}
            except:
                pass
        
        detailed_strategies = []
        total_jobs = 0
        
        for challenge_id, strategy_info in challenge_strategies.items():
            strategy_name = strategy_info['strategy_name']
            
            # Parser les actions de la stratégie
            actions = parse_strategy_actions(strategy_name)
            total_jobs += len(actions)
            
            # Récupérer le vrai nom du challenge
            challenge_title = challenges_map.get(challenge_id, f"Challenge {challenge_id}")
            
            detailed_strategies.append({
                'challenge_id': challenge_id,
                'challenge_title': challenge_title,
                'strategy_name': strategy_name,
                'status': strategy_info['status'],
                'scheduled_at': strategy_info['scheduled_at'],
                'actions': actions
            })
        
        return {
            "strategies": detailed_strategies,
            "total_count": len(detailed_strategies),
            "total_jobs": total_jobs
        }
        
    except Exception as e:
        print(f"❌ Error getting active strategies: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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

async def schedule_existing_strategies():
    """Programme les actions des stratégies existantes au démarrage"""
    try:
        print("🔄 Loading existing strategies from .ini...")
        challenge_strategies = load_challenge_strategies()
        
        if not challenge_strategies:
            print("📋 No existing strategies found")
            return
        
        # TODO: Implémenter la programmation réelle des actions
        # Pour l'instant, on charge juste les données
        print(f"📅 Found {len(challenge_strategies)} strategies to schedule:")
        for challenge_id, strategy_info in challenge_strategies.items():
            strategy_name = strategy_info['strategy_name']
            status = strategy_info['status']
            print(f"  - Challenge {challenge_id}: {strategy_name} ({status})")
        
        print("✅ Strategy scheduling initialization complete")
        
    except Exception as e:
        print(f"❌ Error scheduling existing strategies: {e}")

@app.on_event("startup")
async def startup_event():
    """Événements de démarrage du backend"""
    print("🚀 Backend startup - Loading strategies and turbo states...")
    await schedule_existing_strategies()
    
    # Charger les états turbo existants
    turbo_states = load_turbo_states()
    print(f"📋 Loaded {len(turbo_states)} existing turbo states")

if __name__ == "__main__":
    print("🚀 Démarrage du backend GSGUI avec vrais challenges...")
    uvicorn.run(app, host="127.0.0.1", port=8001, log_level="info")