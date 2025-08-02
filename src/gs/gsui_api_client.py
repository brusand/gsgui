"""
GSGUI API Client - Client pour communiquer avec le backend API
"""

import aiohttp
import asyncio
import ssl
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import json

# Configuration SSL comme dans l'original GSGUI
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

logger = logging.getLogger(__name__)


class GSGUIApiClient:
    """Client pour l'API backend GSGUI"""
    
    def __init__(self, base_url: str = "http://localhost:8001/api/v1"):
        self.base_url = base_url
        self.session: Optional[aiohttp.ClientSession] = None
        self.profile_id: Optional[str] = None
        
    async def __aenter__(self):
        """Context manager entry"""
        if not self.session:
            # Configuration SSL comme dans l'original GSGUI
            connector = aiohttp.TCPConnector(ssl=False)
            timeout = aiohttp.ClientTimeout(total=10)
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout
            )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if self.session:
            await self.session.close()
            self.session = None
    
    async def ensure_session(self):
        """S'assure qu'une session est active"""
        if not self.session:
            # Configuration SSL comme dans l'original GSGUI
            connector = aiohttp.TCPConnector(ssl=False)
            timeout = aiohttp.ClientTimeout(total=10)
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout
            )
    
    # --- Profile Management ---
    
    async def register_profile(self, profile_name: str, gs_token: Optional[str] = None) -> Dict[str, Any]:
        """Enregistre ou connecte un profil"""
        try:
            await self.ensure_session()
            
            data = {
                "profile_name": profile_name,
                "gs_token": gs_token
            }
            
            async with self.session.post(f"{self.base_url}/profiles/register", json=data) as response:
                if response.status == 200:
                    result = await response.json()
                    self.profile_id = result.get('profile_id')
                    logger.info(f"✅ Profile registered: {profile_name}")
                    return result
                else:
                    error_text = await response.text()
                    logger.error(f"❌ Profile registration failed: {response.status} - {error_text}")
                    raise Exception(f"Registration failed: {error_text}")
                    
        except Exception as e:
            logger.error(f"Error registering profile: {e}")
            raise
    
    async def get_profile_info(self, profile_id: Optional[str] = None) -> Dict[str, Any]:
        """Récupère les informations d'un profil"""
        try:
            await self.ensure_session()
            pid = profile_id or self.profile_id
            
            if not pid:
                raise Exception("No profile ID available")
            
            async with self.session.get(f"{self.base_url}/profiles/{pid}") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    raise Exception(f"Failed to get profile info: {error_text}")
                    
        except Exception as e:
            logger.error(f"Error getting profile info: {e}")
            raise
    
    # --- Strategy Management ---
    
    async def schedule_strategy(
        self, 
        challenge_id: str, 
        strategy_name: str, 
        scheduled_at: datetime,
        challenge_title: Optional[str] = None,
        profile_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Programme une stratégie"""
        try:
            await self.ensure_session()
            pid = profile_id or self.profile_id
            
            if not pid:
                raise Exception("No profile ID available")
            
            data = {
                "challenge_id": challenge_id,
                "strategy_name": strategy_name,
                "challenge_title": challenge_title,
                "scheduled_at": scheduled_at.isoformat()
            }
            
            async with self.session.post(f"{self.base_url}/profiles/{pid}/strategies", json=data) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"✅ Strategy scheduled: {strategy_name} for {challenge_id}")
                    return result
                else:
                    error_text = await response.text()
                    logger.error(f"❌ Strategy scheduling failed: {response.status} - {error_text}")
                    raise Exception(f"Strategy scheduling failed: {error_text}")
                    
        except Exception as e:
            logger.error(f"Error scheduling strategy: {e}")
            raise
    
    async def list_strategies(self, profile_id: Optional[str] = None, status: Optional[str] = None) -> Dict[str, Any]:
        """Liste les stratégies programmées"""
        try:
            await self.ensure_session()
            pid = profile_id or self.profile_id
            
            if not pid:
                raise Exception("No profile ID available")
            
            params = {}
            if status:
                params['status'] = status
            
            async with self.session.get(f"{self.base_url}/profiles/{pid}/strategies", params=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    raise Exception(f"Failed to list strategies: {error_text}")
                    
        except Exception as e:
            logger.error(f"Error listing strategies: {e}")
            raise
    
    async def cancel_strategy(self, strategy_id: str, profile_id: Optional[str] = None) -> Dict[str, Any]:
        """Annule une stratégie programmée"""
        try:
            await self.ensure_session()
            pid = profile_id or self.profile_id
            
            if not pid:
                raise Exception("No profile ID available")
            
            async with self.session.delete(f"{self.base_url}/profiles/{pid}/strategies/{strategy_id}") as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"✅ Strategy cancelled: {strategy_id}")
                    return result
                else:
                    error_text = await response.text()
                    logger.error(f"❌ Strategy cancellation failed: {response.status} - {error_text}")
                    raise Exception(f"Strategy cancellation failed: {error_text}")
                    
        except Exception as e:
            logger.error(f"Error cancelling strategy: {e}")
            raise
    
    async def cancel_challenge_strategies(self, challenge_id: str, profile_id: Optional[str] = None) -> int:
        """Annule toutes les stratégies d'un challenge"""
        try:
            # Récupérer toutes les stratégies
            strategies = await self.list_strategies(profile_id)
            
            cancelled_count = 0
            for strategy in strategies.get('strategies', []):
                if strategy.get('challenge_id') == challenge_id and strategy.get('status') == 'pending':
                    try:
                        await self.cancel_strategy(strategy.get('strategy_id'), profile_id)
                        cancelled_count += 1
                    except Exception as e:
                        logger.warning(f"Failed to cancel strategy {strategy.get('strategy_id')}: {e}")
            
            return cancelled_count
            
        except Exception as e:
            logger.error(f"Error cancelling challenge strategies: {e}")
            return 0
    
    async def get_available_strategies(self) -> Dict[str, Any]:
        """Récupère les stratégies disponibles"""
        try:
            await self.ensure_session()
            
            async with self.session.get(f"{self.base_url}/available") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    raise Exception(f"Failed to get available strategies: {error_text}")
                    
        except Exception as e:
            logger.error(f"Error getting available strategies: {e}")
            raise
    
    async def update_strategy(
        self, 
        strategy_id: str, 
        strategy_name: Optional[str] = None,
        scheduled_at: Optional[str] = None,
        status: Optional[str] = None,
        profile_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Met à jour une stratégie existante"""
        try:
            await self.ensure_session()
            pid = profile_id or self.profile_id
            
            if not pid:
                raise Exception("No profile ID available")
            
            # Construire les données à mettre à jour
            update_data = {}
            if strategy_name is not None:
                update_data["strategy_name"] = strategy_name
            if scheduled_at is not None:
                update_data["scheduled_at"] = scheduled_at
            if status is not None:
                update_data["status"] = status
            
            if not update_data:
                raise Exception("No update data provided")
            
            async with self.session.put(
                f"{self.base_url}/{pid}/strategies/{strategy_id}",
                json=update_data
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    raise Exception(f"Failed to update strategy: {error_text}")
                    
        except Exception as e:
            logger.error(f"Error updating strategy {strategy_id}: {e}")
            raise
    
    # --- Turbo Management ---
    
    async def execute_turbo(
        self, 
        challenge_id: str, 
        challenge_title: Optional[str] = None,
        challenge_time_left: Optional[str] = None,
        algorithm: Optional[str] = None,
        profile_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Exécute un turbo"""
        try:
            await self.ensure_session()
            pid = profile_id or self.profile_id
            
            if not pid:
                raise Exception("No profile ID available")
            
            data = {
                "challenge_id": challenge_id,
                "challenge_title": challenge_title,
                "challenge_time_left": challenge_time_left,
                "algorithm": algorithm
            }
            
            async with self.session.post(f"{self.base_url}/profiles/{pid}/turbo/execute", json=data) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"🚀 Turbo execution started: {challenge_id}")
                    return result
                else:
                    error_text = await response.text()
                    logger.error(f"❌ Turbo execution failed: {response.status} - {error_text}")
                    raise Exception(f"Turbo execution failed: {error_text}")
                    
        except Exception as e:
            logger.error(f"Error executing turbo: {e}")
            raise
    
    async def get_turbo_status(self, challenge_id: str, profile_id: Optional[str] = None) -> Dict[str, Any]:
        """Récupère le statut turbo d'un challenge"""
        try:
            await self.ensure_session()
            pid = profile_id or self.profile_id
            
            if not pid:
                raise Exception("No profile ID available")
            
            async with self.session.get(f"{self.base_url}/profiles/{pid}/turbo/status/{challenge_id}") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    raise Exception(f"Failed to get turbo status: {error_text}")
                    
        except Exception as e:
            logger.error(f"Error getting turbo status: {e}")
            raise
    
    async def cancel_turbo(self, challenge_id: str, profile_id: Optional[str] = None) -> Dict[str, Any]:
        """Annule l'exécution turbo"""
        try:
            await self.ensure_session()
            pid = profile_id or self.profile_id
            
            if not pid:
                raise Exception("No profile ID available")
            
            async with self.session.delete(f"{self.base_url}/profiles/{pid}/turbo/cancel/{challenge_id}") as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"✅ Turbo cancelled: {challenge_id}")
                    return result
                else:
                    error_text = await response.text()
                    logger.error(f"❌ Turbo cancellation failed: {response.status} - {error_text}")
                    raise Exception(f"Turbo cancellation failed: {error_text}")
                    
        except Exception as e:
            logger.error(f"Error cancelling turbo: {e}")
            raise
    
    async def get_turbo_settings(self, profile_id: Optional[str] = None) -> Dict[str, Any]:
        """Récupère les paramètres turbo"""
        try:
            await self.ensure_session()
            pid = profile_id or self.profile_id
            
            if not pid:
                raise Exception("No profile ID available")
            
            async with self.session.get(f"{self.base_url}/profiles/{pid}/turbo/settings") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    raise Exception(f"Failed to get turbo settings: {error_text}")
                    
        except Exception as e:
            logger.error(f"Error getting turbo settings: {e}")
            raise
    
    async def get_available_algorithms(self) -> Dict[str, Any]:
        """Récupère les algorithmes turbo disponibles"""
        try:
            await self.ensure_session()
            
            async with self.session.get(f"{self.base_url}/algorithms") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    raise Exception(f"Failed to get available algorithms: {error_text}")
                    
        except Exception as e:
            logger.error(f"Error getting available algorithms: {e}")
            raise
    
    # --- Challenge Management (legacy compatibility) ---
    
    async def get_challenges(self, user_token: str) -> List[Dict[str, Any]]:
        """Récupère les challenges (compatibilité legacy)"""
        try:
            await self.ensure_session()
            
            params = {'user_token': user_token}
            url = f"{self.base_url}/challenges/"
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    result = await response.json()
                    challenges = result.get('challenges', [])
                    return challenges
                else:
                    error_text = await response.text()
                    logger.error(f"❌ Failed to get challenges: {response.status} - {error_text}")
                    return []
                    
        except Exception as e:
            logger.error(f"Error getting challenges: {e}")
            return []
    
    async def execute_simple_vote(self, challenge_url: str, vote_count: int, user_token: str) -> Dict[str, Any]:
        """Exécute un vote simple (compatibilité legacy)"""
        try:
            await self.ensure_session()
            
            data = {
                "challenge_url": challenge_url,
                "vote_count": vote_count
            }
            
            params = {'user_token': user_token}
            
            async with self.session.post(f"{self.base_url}/challenges/simple-vote", json=data, params=params) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"✅ Vote executed: {vote_count} votes")
                    return result
                else:
                    error_text = await response.text()
                    logger.error(f"❌ Vote execution failed: {response.status} - {error_text}")
                    return {"success": False, "message": error_text}
                    
        except Exception as e:
            logger.error(f"Error executing vote: {e}")
            return {"success": False, "message": str(e)}