"""
WebSocket Connection Manager - Gestion temps réel pour GSGUI
"""

from typing import Dict, List, Set, Optional, Any
import json
import asyncio
import logging
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class RealtimeEvent:
    """Structure d'un événement temps réel"""
    type: str
    user_id: str
    timestamp: str
    data: Dict[str, Any]
    
    def to_json(self) -> str:
        """Convertit l'événement en JSON"""
        return json.dumps(asdict(self))


class RealtimeEventTypes:
    """Types d'événements temps réel"""
    # Challenges
    CHALLENGE_UPDATE = "challenge_update"
    CHALLENGE_NEW = "challenge_new"
    CHALLENGE_ENDED = "challenge_ended"
    
    # Stratégies
    STRATEGY_STARTED = "strategy_started"
    STRATEGY_STEP = "strategy_step"
    STRATEGY_COMPLETED = "strategy_completed"
    STRATEGY_FAILED = "strategy_failed"
    STRATEGY_CANCELLED = "strategy_cancelled"
    
    # Votes
    VOTE_EXECUTED = "vote_executed"
    VOTE_FAILED = "vote_failed"
    
    # Turbo
    TURBO_STARTED = "turbo_started"
    TURBO_COMPLETED = "turbo_completed"
    TURBO_FAILED = "turbo_failed"
    TURBO_CANCELLED = "turbo_cancelled"
    TURBO_LOG = "turbo_log"
    TURBO_PAIR_RESULT = "turbo_pair_result"
    
    # Classements
    RANKING_CHANGE = "ranking_change"
    VOTES_UPDATE = "votes_update"
    
    # Alertes
    TIME_WARNING = "time_warning"
    ERROR_ALERT = "error_alert"
    
    # Système
    HEARTBEAT = "heartbeat"
    SYSTEM_MESSAGE = "system_message"
    #log
    BROADCAST_LOG = "broadcast_log"


class ConnectionManager:
    """
    Gestionnaire de connexions WebSocket
    Gère les connexions par utilisateur et diffuse les événements
    """
    
    def __init__(self):
        # Connexions actives par utilisateur
        self.active_connections: Dict[str, List[WebSocket]] = {}
        
        # Métadonnées des connexions
        self.connection_metadata: Dict[WebSocket, Dict[str, Any]] = {}
        
        # Statistiques
        self.total_connections = 0
        self.total_messages_sent = 0
        
        logger.info("🔌 WebSocket Connection Manager initialized")
    
    async def connect(self, websocket: WebSocket, user_id: str, metadata: Optional[Dict[str, Any]] = None):
        """Établit une nouvelle connexion WebSocket"""
        try:
            await websocket.accept()
            
            # Ajouter à la liste des connexions
            if user_id not in self.active_connections:
                self.active_connections[user_id] = []
            
            self.active_connections[user_id].append(websocket)
            
            # Stocker les métadonnées
            connection_info = {
                "user_id": user_id,
                "connected_at": datetime.now().isoformat(),
                "client_info": metadata or {}
            }
            self.connection_metadata[websocket] = connection_info
            
            self.total_connections += 1
            
            logger.info(f"✅ WebSocket connected: user {user_id} (total: {len(self.active_connections)})")
            
            # Envoyer un message de bienvenue
            await self.send_personal_message(user_id, {
                "type": RealtimeEventTypes.SYSTEM_MESSAGE,
                "message": "Connected to GSGUI Backend",
                "timestamp": datetime.now().isoformat(),
                "connection_id": str(id(websocket))
            })
            
        except Exception as e:
            logger.error(f"Error connecting WebSocket for user {user_id}: {e}")
            raise
    
    def disconnect(self, websocket: WebSocket, user_id: str):
        """Ferme une connexion WebSocket"""
        try:
            # Supprimer de la liste des connexions
            if user_id in self.active_connections:
                if websocket in self.active_connections[user_id]:
                    self.active_connections[user_id].remove(websocket)
                
                # Supprimer l'utilisateur si plus de connexions
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]
            
            # Supprimer les métadonnées
            if websocket in self.connection_metadata:
                del self.connection_metadata[websocket]
            
            logger.info(f"❌ WebSocket disconnected: user {user_id} (remaining: {len(self.active_connections)})")
            
        except Exception as e:
            logger.error(f"Error disconnecting WebSocket for user {user_id}: {e}")
    
    async def send_personal_message(self, user_id: str, message: Dict[str, Any]):
        """Envoie un message à un utilisateur spécifique"""
        print(f"🔥 send_personal_message - user_id: {user_id}, message_type: {message.get('type')}")
        if user_id in self.active_connections:
            # Créer l'événement
            event = RealtimeEvent(
                type=message.get("type", "message"),
                user_id=user_id,
                timestamp=datetime.now().isoformat(),
                data=message
            )
            
            # Envoyer à toutes les connexions de l'utilisateur
            disconnected_sockets = []
            print(f"🔥 Envoi à {len(self.active_connections[user_id])} connexion(s) pour {user_id}")
            for websocket in self.active_connections[user_id]:
                try:
                    json_message = event.to_json()
                    print(f"🔥 Envoi WebSocket JSON: {json_message}")
                    await websocket.send_text(json_message)
                    self.total_messages_sent += 1
                    print(f"🔥 ✅ Message envoyé avec succès via WebSocket")
                except Exception as e:
                    print(f"🔥 ❌ Erreur envoi WebSocket: {e}")
                    logger.error(f"Error sending message to user {user_id}: {e}")
                    disconnected_sockets.append(websocket)
            
            # Nettoyer les connexions fermées
            for ws in disconnected_sockets:
                self.disconnect(ws, user_id)
    
    async def broadcast_to_all(self, message: Dict[str, Any], exclude_user: Optional[str] = None):
        """Diffuse un message à tous les utilisateurs connectés"""
        for user_id in list(self.active_connections.keys()):
            if exclude_user and user_id == exclude_user:
                continue
            
            await self.send_personal_message(user_id, message)
    
    async def broadcast_to_users(self, user_ids: List[str], message: Dict[str, Any]):
        """Diffuse un message à une liste d'utilisateurs"""
        for user_id in user_ids:
            if user_id in self.active_connections:
                await self.send_personal_message(user_id, message)
    
    # Méthodes spécialisées pour les événements GSGUI
    
    async def notify_challenge_update(self, user_id: str, challenge_data: Dict[str, Any]):
        """Notifie la mise à jour d'un challenge"""
        await self.send_personal_message(user_id, {
            "type": RealtimeEventTypes.CHALLENGE_UPDATE,
            "challenge": challenge_data
        })
    
    async def notify_strategy_started(self, user_id: str, strategy_id: str, strategy_data: Dict[str, Any]):
        """Notifie le début d'une stratégie"""
        await self.send_personal_message(user_id, {
            "type": RealtimeEventTypes.STRATEGY_STARTED,
            "strategy_id": strategy_id,
            "strategy": strategy_data
        })
    
    async def notify_strategy_step(self, user_id: str, strategy_id: str, step_number: int, action_data: Dict[str, Any]):
        """Notifie l'exécution d'une étape de stratégie"""
        await self.send_personal_message(user_id, {
            "type": RealtimeEventTypes.STRATEGY_STEP,
            "strategy_id": strategy_id,
            "step_number": step_number,
            "action": action_data
        })
    
    async def notify_strategy_completed(self, user_id: str, strategy_id: str, success: bool, results: Dict[str, Any]):
        """Notifie la fin d'une stratégie"""
        await self.send_personal_message(user_id, {
            "type": RealtimeEventTypes.STRATEGY_COMPLETED,
            "strategy_id": strategy_id,
            "success": success,
            "results": results
        })
    
    async def notify_vote_executed(self, user_id: str, challenge_id: str, vote_count: int, success: bool):
        """Notifie l'exécution d'un vote"""
        await self.send_personal_message(user_id, {
            "type": RealtimeEventTypes.VOTE_EXECUTED,
            "challenge_id": challenge_id,
            "vote_count": vote_count,
            "success": success,
            "timestamp": datetime.now().isoformat()
        })
    
    async def notify_turbo_started(self, user_id: str, turbo_id: str, challenge_id: str, algorithm: str):
        """Notifie le début d'un turbo"""
        await self.send_personal_message(user_id, {
            "type": RealtimeEventTypes.TURBO_STARTED,
            "turbo_id": turbo_id,
            "challenge_id": challenge_id,
            "algorithm": algorithm,
            "timestamp": datetime.now().isoformat()
        })
    
    async def notify_turbo_completed(self, user_id: str, turbo_id: str, result_data: Dict[str, Any]):
        """Notifie la fin réussie d'un turbo"""
        await self.send_personal_message(user_id, {
            "type": RealtimeEventTypes.TURBO_COMPLETED,
            "turbo_id": turbo_id,
            "result": result_data,
            "timestamp": datetime.now().isoformat()
        })
    
    async def notify_turbo_failed(self, user_id: str, turbo_id: str, error_message: str):
        """Notifie l'échec d'un turbo"""
        await self.send_personal_message(user_id, {
            "type": RealtimeEventTypes.TURBO_FAILED,
            "turbo_id": turbo_id,
            "error_message": error_message,
            "timestamp": datetime.now().isoformat()
        })
    
    async def notify_turbo_log(self, user_id: str, turbo_id: str, level: str, message: str):
        """Notifie un log de turbo"""
        await self.send_personal_message(user_id, {
            "type": RealtimeEventTypes.TURBO_LOG,
            "turbo_id": turbo_id,
            "level": level,
            "message": message,
            "timestamp": datetime.now().isoformat()
        })
    
    async def notify_turbo_update(self, user_id: str, turbo_id: str, challenge_id: str, update_type: str, data: Dict[str, Any]):
        """Notifie une mise à jour turbo générique"""
        await self.send_personal_message(user_id, {
            "type": "turbo_update",
            "turbo_id": turbo_id,
            "challenge_id": challenge_id,
            "update_type": update_type,
            "data": data,
            "timestamp": datetime.now().isoformat()
        })
    
    async def notify_ranking_change(self, user_id: str, challenge_id: str, old_rank: int, new_rank: int, votes: int):
        """Notifie un changement de classement"""
        await self.send_personal_message(user_id, {
            "type": RealtimeEventTypes.RANKING_CHANGE,
            "challenge_id": challenge_id,
            "old_rank": old_rank,
            "new_rank": new_rank,
            "votes": votes,
            "timestamp": datetime.now().isoformat()
        })
    
    async def notify_time_warning(self, user_id: str, challenge_id: str, time_left: str):
        """Notifie une alerte de temps"""
        await self.send_personal_message(user_id, {
            "type": RealtimeEventTypes.TIME_WARNING,
            "challenge_id": challenge_id,
            "time_left": time_left,
            "timestamp": datetime.now().isoformat()
        })
    
    async def notify_error(self, user_id: str, error_type: str, message: str, context: Optional[Dict[str, Any]] = None):
        """Notifie une erreur"""
        await self.send_personal_message(user_id, {
            "type": RealtimeEventTypes.ERROR_ALERT,
            "error_type": error_type,
            "message": message,
            "context": context or {},
            "timestamp": datetime.now().isoformat()
        })
    async def notify_broadcast_log(self, user_id: str, level: str, message: str):
        """Notifie un log"""
        print(f"🔥 notify_broadcast_log APPELÉ - user_id: {user_id}, level: {level}, message: {message}")
        print(f"🔥 Connexions actives: {list(self.active_connections.keys())}")
        
        message_data = {
            "type": RealtimeEventTypes.BROADCAST_LOG,
            "level": level,  # 'info', 'success', 'error', 'warning'
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        print(f"🔥 Message à envoyer: {message_data}")
        
        await self.send_personal_message(user_id, message_data)
    # Méthodes utilitaires
    
    def get_connected_users(self) -> List[str]:
        """Retourne la liste des utilisateurs connectés"""
        return list(self.active_connections.keys())
    
    def get_user_connection_count(self, user_id: str) -> int:
        """Retourne le nombre de connexions pour un utilisateur"""
        return len(self.active_connections.get(user_id, []))
    
    def get_total_connections(self) -> int:
        """Retourne le nombre total de connexions"""
        return sum(len(connections) for connections in self.active_connections.values())
    
    def get_statistics(self) -> Dict[str, Any]:
        """Retourne les statistiques des connexions"""
        return {
            "total_users": len(self.active_connections),
            "total_connections": self.get_total_connections(),
            "total_messages_sent": self.total_messages_sent,
            "users_connected": list(self.active_connections.keys())
        }
    
    async def send_heartbeat(self):
        """Envoie un heartbeat à tous les clients connectés"""
        heartbeat_message = {
            "type": RealtimeEventTypes.HEARTBEAT,
            "timestamp": datetime.now().isoformat(),
            "server_time": datetime.now().isoformat()
        }
        
        await self.broadcast_to_all(heartbeat_message)
    
    async def start_heartbeat_task(self, interval: int = 30):
        """Démarre la tâche de heartbeat périodique"""
        async def heartbeat_loop():
            while True:
                await asyncio.sleep(interval)
                try:
                    await self.send_heartbeat()
                except Exception as e:
                    logger.error(f"Error sending heartbeat: {e}")
        
        # Lancer la tâche en arrière-plan
        asyncio.create_task(heartbeat_loop())
        logger.info(f"🫀 Heartbeat task started (interval: {interval}s)")


# Instance globale du gestionnaire de connexions
connection_manager = ConnectionManager()