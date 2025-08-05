from datetime import datetime
from typing import Dict, Any, Optional
from backend.app.websockets.connection_manager import connection_manager, RealtimeEventTypes


async def notify_broadcast_log(profile_id: str, level: str, message: str):
    """Notifie un message de log turbo"""
    await connection_manager.send_personal_message(profile_id, {
        "type": RealtimeEventTypes.BROADCAST_LOG,
        "level": level,  # 'info', 'success', 'error', 'warning'
        "message": message,
        "timestamp": datetime.now().isoformat()
    })