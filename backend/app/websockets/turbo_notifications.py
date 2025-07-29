"""
Turbo WebSocket Notifications - Extension for connection_manager
"""

from datetime import datetime
from typing import Dict, Any, Optional
from app.websockets.connection_manager import connection_manager, RealtimeEventTypes


async def notify_turbo_started(profile_id: str, turbo_data: Dict[str, Any]):
    """Notifie le démarrage d'un turbo"""
    await connection_manager.send_personal_message(profile_id, {
        "type": RealtimeEventTypes.TURBO_STARTED,
        "turbo_id": turbo_data.get('turbo_id'),
        "challenge_id": turbo_data.get('challenge_id'),
        "algorithm": turbo_data.get('algorithm_used'),
        "timestamp": datetime.now().isoformat(),
        "data": turbo_data
    })


async def notify_turbo_completed(profile_id: str, turbo_id: str, result: Dict[str, Any]):
    """Notifie la completion d'un turbo"""
    await connection_manager.send_personal_message(profile_id, {
        "type": RealtimeEventTypes.TURBO_COMPLETED,
        "turbo_id": turbo_id,
        "challenge_id": result.get('challenge_id'),
        "success": result.get('success', False),
        "pairs_processed": result.get('pairs_processed', 0),
        "successful_pairs": result.get('successful_pairs', 0),
        "timestamp": datetime.now().isoformat(),
        "result": result
    })


async def notify_turbo_failed(profile_id: str, turbo_id: str, error_message: str):
    """Notifie l'échec d'un turbo"""
    await connection_manager.send_personal_message(profile_id, {
        "type": RealtimeEventTypes.TURBO_FAILED,
        "turbo_id": turbo_id,
        "error_message": error_message,
        "timestamp": datetime.now().isoformat()
    })


async def notify_turbo_cancelled(profile_id: str, challenge_id: str):
    """Notifie l'annulation d'un turbo"""
    await connection_manager.send_personal_message(profile_id, {
        "type": RealtimeEventTypes.TURBO_CANCELLED,
        "challenge_id": challenge_id,
        "timestamp": datetime.now().isoformat()
    })


async def notify_turbo_log(profile_id: str, turbo_id: str, level: str, message: str, pair_number: Optional[int] = None):
    """Notifie un message de log turbo"""
    await connection_manager.send_personal_message(profile_id, {
        "type": RealtimeEventTypes.TURBO_LOG,
        "turbo_id": turbo_id,
        "level": level,  # 'info', 'success', 'error', 'warning'
        "message": message,
        "pair_number": pair_number,
        "timestamp": datetime.now().isoformat()
    })


async def notify_turbo_pair_result(profile_id: str, turbo_id: str, pair_data: Dict[str, Any]):
    """Notifie le résultat d'une paire turbo"""
    await connection_manager.send_personal_message(profile_id, {
        "type": RealtimeEventTypes.TURBO_PAIR_RESULT,
        "turbo_id": turbo_id,
        "pair_number": pair_data.get('pair_number'),
        "success": pair_data.get('success', False),
        "algorithm_choice": pair_data.get('algorithm_choice'),
        "actual_winner": pair_data.get('actual_winner'),
        "scores": {
            "first": pair_data.get('first_score'),
            "second": pair_data.get('second_score')
        },
        "is_retry": pair_data.get('is_retry', False),
        "timestamp": datetime.now().isoformat(),
        "data": pair_data
    })


async def notify_strategy_scheduled(profile_id: str, strategy_data: Dict[str, Any]):
    """Notifie la programmation d'une stratégie"""
    await connection_manager.send_personal_message(profile_id, {
        "type": RealtimeEventTypes.STRATEGY_STARTED,
        "strategy_id": strategy_data.get('strategy_id'),
        "challenge_id": strategy_data.get('challenge_id'),
        "strategy_name": strategy_data.get('strategy_name'),
        "scheduled_at": strategy_data.get('scheduled_at'),
        "timestamp": datetime.now().isoformat(),
        "data": strategy_data
    })


async def notify_strategy_executed(profile_id: str, execution_result: Dict[str, Any]):
    """Notifie l'exécution d'une stratégie"""
    await connection_manager.send_personal_message(profile_id, {
        "type": RealtimeEventTypes.STRATEGY_COMPLETED,
        "strategy_id": execution_result.get('strategy_id'),
        "challenge_id": execution_result.get('challenge_id'),
        "success": execution_result.get('success', False),
        "votes_cast": execution_result.get('votes_cast', 0),
        "timestamp": datetime.now().isoformat(),
        "result": execution_result
    })


async def notify_strategy_status_changed(profile_id: str, strategy_id: str, old_status: str, new_status: str):
    """Notifie un changement de statut de stratégie"""
    await connection_manager.send_personal_message(profile_id, {
        "type": RealtimeEventTypes.STRATEGY_STEP,
        "strategy_id": strategy_id,
        "old_status": old_status,
        "new_status": new_status,
        "timestamp": datetime.now().isoformat()
    })


async def notify_strategy_deleted(profile_id: str, strategy_id: str):
    """Notifie la suppression d'une stratégie"""
    await connection_manager.send_personal_message(profile_id, {
        "type": RealtimeEventTypes.STRATEGY_CANCELLED,
        "strategy_id": strategy_id,
        "timestamp": datetime.now().isoformat()
    })


# Ajouter les méthodes à connection_manager
connection_manager.notify_turbo_started = notify_turbo_started
connection_manager.notify_turbo_completed = notify_turbo_completed
connection_manager.notify_turbo_failed = notify_turbo_failed
connection_manager.notify_turbo_cancelled = notify_turbo_cancelled
connection_manager.notify_turbo_log = notify_turbo_log
connection_manager.notify_turbo_pair_result = notify_turbo_pair_result
connection_manager.notify_strategy_scheduled = notify_strategy_scheduled
connection_manager.notify_strategy_executed = notify_strategy_executed
connection_manager.notify_strategy_status_changed = notify_strategy_status_changed
connection_manager.notify_strategy_deleted = notify_strategy_deleted