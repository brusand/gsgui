"""
Simple API Client - Version simplifiée sans problèmes SSL
"""

import requests
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime

class SimpleApiClient:
    """Client API simple avec requests (synchrone)"""
    
    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api/v1"
        
    def register_profile(self, profile_name: str, gs_token: str = None) -> Dict[str, Any]:
        """Enregistre un profil"""
        try:
            data = {
                "profile_name": profile_name,
                "gs_token": gs_token
            }
            response = requests.post(f"{self.api_url}/profiles/register", json=data, timeout=5)
            if response.status_code == 200:
                return response.json()
            else:
                return {"status": "error", "message": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def get_challenges(self, user_token: str) -> List[Dict[str, Any]]:
        """Récupère les challenges"""
        try:
            params = {'user_token': user_token}
            response = requests.get(f"{self.api_url}/challenges/", params=params, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                return data.get('challenges', [])
            else:
                print(f"❌ API Error: {response.status_code}")
                return []
        except Exception as e:
            print(f"❌ Connection Error: {e}")
            return []
    
    def schedule_strategy(self, challenge_id: str, strategy_name: str, 
                         scheduled_at: datetime, challenge_title: str = None) -> Dict[str, Any]:
        """Programme une stratégie"""
        try:
            data = {
                "challenge_id": challenge_id,
                "strategy_name": strategy_name,
                "scheduled_at": scheduled_at.isoformat(),
                "challenge_title": challenge_title
            }
            
            # Utiliser le profil par défaut
            profile_id = "bruno"  # Ou récupérer dynamiquement
            
            response = requests.post(f"{self.api_url}/profiles/{profile_id}/strategies", 
                                   json=data, timeout=5)
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"status": "error", "message": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def list_strategies(self, profile_id: str = "bruno") -> Dict[str, Any]:
        """Liste les stratégies"""
        try:
            response = requests.get(f"{self.api_url}/profiles/{profile_id}/strategies", timeout=5)
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"strategies": [], "total_count": 0}
        except Exception as e:
            return {"strategies": [], "total_count": 0}
    
    def cancel_challenge_strategies(self, challenge_id: str, profile_id: str = "bruno") -> int:
        """Annule toutes les stratégies d'un challenge"""
        try:
            # Récupérer les stratégies existantes
            strategies_data = self.list_strategies(profile_id)
            strategies = strategies_data.get('strategies', [])
            
            cancelled = 0
            for strategy in strategies:
                if strategy.get('challenge_id') == challenge_id and strategy.get('status') == 'pending':
                    strategy_id = strategy.get('strategy_id')
                    try:
                        response = requests.delete(f"{self.api_url}/profiles/{profile_id}/strategies/{strategy_id}", 
                                                 timeout=5)
                        if response.status_code == 200:
                            cancelled += 1
                    except Exception as e:
                        print(f"❌ Error cancelling strategy {strategy_id}: {e}")
            
            return cancelled
        except Exception as e:
            print(f"❌ Error in cancel_challenge_strategies: {e}")
            return 0
    
    def execute_turbo(self, challenge_id: str, challenge_title: str = None, 
                     challenge_time_left: str = None) -> Dict[str, Any]:
        """Exécute un turbo"""
        try:
            data = {
                "challenge_id": challenge_id,
                "challenge_title": challenge_title,
                "challenge_time_left": challenge_time_left
            }
            
            profile_id = "bruno"
            response = requests.post(f"{self.api_url}/profiles/{profile_id}/turbo/execute", 
                                   json=data, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"status": "error", "message": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def execute_simple_vote(self, challenge_url: str, vote_count: int, user_token: str) -> Dict[str, Any]:
        """Exécute un vote simple"""
        try:
            data = {
                "challenge_url": challenge_url,
                "vote_count": vote_count
            }
            
            params = {'user_token': user_token}
            response = requests.post(f"{self.api_url}/challenges/simple-vote", 
                                   json=data, params=params, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"success": False, "message": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"success": False, "message": str(e)}