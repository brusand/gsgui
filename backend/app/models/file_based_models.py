"""
File-based models using ConfigObj - Alternative to SQLAlchemy models
Compatible avec la persistance .ini de gsui.py
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
import uuid

from app.services.config_manager import config_manager


class User(BaseModel):
    """Modèle utilisateur basé sur fichier"""
    id: str
    username: str
    user_name: str = ""
    xtoken: str
    turbo_algorithm: str = "hybrid"
    auto_optimize_turbo: bool = True
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    @classmethod
    def create(cls, user_id: str, username: str, xtoken: str, **kwargs) -> Optional['User']:
        """Crée un nouvel utilisateur"""
        user_data = {
            'user_name': kwargs.get('user_name', username),
            'xtoken': xtoken,
            'turbo_algorithm': kwargs.get('turbo_algorithm', 'hybrid'),
            'auto_optimize_turbo': kwargs.get('auto_optimize_turbo', True)
        }
        
        if config_manager.create_user(user_id, user_data):
            return cls(
                id=user_id,
                username=username,
                user_name=user_data['user_name'],
                xtoken=user_data['xtoken'],
                turbo_algorithm=user_data['turbo_algorithm'],
                auto_optimize_turbo=user_data['auto_optimize_turbo']
            )
        return None
    
    @classmethod
    def get_by_id(cls, user_id: str) -> Optional['User']:
        """Récupère un utilisateur par son ID"""
        user_data = config_manager.get_user(user_id)
        if user_data:
            return cls(
                id=user_id,
                username=user_data.get('user_name', user_id),
                **user_data
            )
        return None
    
    @classmethod
    def get_by_token(cls, xtoken: str) -> Optional['User']:
        """Récupère un utilisateur par son token"""
        users = config_manager.list_users()
        for user_id in users:
            user_data = config_manager.get_user(user_id)
            if user_data and user_data.get('xtoken') == xtoken:
                return cls(
                    id=user_id,
                    username=user_data.get('user_name', user_id),
                    **user_data
                )
        return None
    
    @classmethod
    def list_all(cls) -> List['User']:
        """Liste tous les utilisateurs"""
        users = []
        user_ids = config_manager.list_users()
        
        for user_id in user_ids:
            user = cls.get_by_id(user_id)
            if user:
                users.append(user)
        
        return users
    
    def update(self, updates: Dict[str, Any]) -> bool:
        """Met à jour l'utilisateur"""
        if config_manager.update_user(self.id, updates):
            # Mettre à jour l'instance locale
            for key, value in updates.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        return False
    
    def save_challenge(self, challenge_id: str, challenge_data: Dict[str, Any]) -> bool:
        """Sauvegarde un challenge pour cet utilisateur"""
        return config_manager.save_user_challenge(self.id, challenge_id, challenge_data)
    
    def get_challenges(self) -> Dict[str, Any]:
        """Récupère tous les challenges de cet utilisateur"""
        return config_manager.get_user_challenges(self.id)
    
    def get_processes(self) -> Dict[str, str]:
        """Récupère tous les processus de cet utilisateur"""
        return config_manager.get_user_processes(self.id)


class Challenge(BaseModel):
    """Modèle challenge basé sur fichier"""
    id: str
    title: str
    url: str
    end_time: datetime
    time_left_days: int = 0
    time_left_hours: int = 0
    time_left_minutes: int = 0
    time_left_seconds: int = 0
    votes: int = 0
    rank: int = 0
    level: Optional[str] = None
    exposure: int = 0
    gps: int = 0
    selected_strategy: Optional[str] = None
    status: str = ""
    turbo_status: str = ""
    current_process_id: Optional[str] = None
    user_id: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    @classmethod
    def create_from_api_data(cls, user_id: str, api_challenge_data: Dict[str, Any]) -> 'Challenge':
        """Crée un Challenge à partir des données API GuruShots"""
        time_left = api_challenge_data.get('time_left', {})
        
        challenge = cls(
            id=api_challenge_data['id'],
            title=api_challenge_data['title'],
            url=api_challenge_data['url'],
            end_time=api_challenge_data['end_time'],
            time_left_days=time_left.get('days', 0),
            time_left_hours=time_left.get('hours', 0),
            time_left_minutes=time_left.get('minutes', 0),
            time_left_seconds=time_left.get('seconds', 0),
            votes=api_challenge_data.get('votes', 0),
            rank=api_challenge_data.get('rank', 0),
            level=api_challenge_data.get('level'),
            exposure=api_challenge_data.get('exposure', 0),
            gps=api_challenge_data.get('gps', 0),
            user_id=user_id,
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )
        
        return challenge
    
    def save(self) -> bool:
        """Sauvegarde le challenge"""
        challenge_data = {
            'title': self.title,
            'selected_strategy': self.selected_strategy,
            'status': self.status,
            'votes': self.votes,
            'rank': self.rank,
            'scheduled_at': self.created_at or datetime.now().isoformat()
        }
        
        return config_manager.save_user_challenge(self.user_id, self.id, challenge_data)
    
    def update_status(self, status: str, additional_data: Optional[Dict] = None) -> bool:
        """Met à jour le statut du challenge"""
        if config_manager.update_challenge_status(self.user_id, self.id, status, additional_data):
            self.status = status
            if additional_data:
                for key, value in additional_data.items():
                    if hasattr(self, key):
                        setattr(self, key, value)
            return True
        return False
    
    @property
    def time_left_formatted(self) -> str:
        """Format le temps restant"""
        return f"{self.time_left_days}D {self.time_left_hours}H {self.time_left_minutes}M {self.time_left_seconds}S"


class Strategy(BaseModel):
    """Modèle stratégie basé sur fichier"""
    name: str
    description: str
    config: Dict[str, str]
    
    @classmethod
    def get_by_name(cls, strategy_name: str) -> Optional['Strategy']:
        """Récupère une stratégie par son nom"""
        strategy_data = config_manager.get_strategy(strategy_name)
        if strategy_data:
            description = strategy_data.pop('description', f'Stratégie {strategy_name}')
            return cls(
                name=strategy_name,
                description=description,
                config=strategy_data
            )
        return None
    
    @classmethod
    def list_all(cls) -> List['Strategy']:
        """Liste toutes les stratégies"""
        strategies = []
        strategies_data = config_manager.list_strategies()
        
        for name, data in strategies_data.items():
            description = data.get('description', f'Stratégie {name}')
            config = {k: v for k, v in data.items() if k != 'description'}
            
            strategies.append(cls(
                name=name,
                description=description,
                config=config
            ))
        
        return strategies
    
    def save(self) -> bool:
        """Sauvegarde la stratégie"""
        strategy_config = self.config.copy()
        strategy_config['description'] = self.description
        
        return config_manager.create_strategy(self.name, strategy_config)


class TurboHistory(BaseModel):
    """Modèle historique turbo basé sur fichier"""
    id: str
    challenge_id: str
    challenge_title: str
    time_left: str
    algorithm: str
    strategy_description: str
    success: bool
    photo1_id: str
    photo1_ratio: Optional[float] = None
    photo1_votes: Optional[int] = None
    photo1_rank: Optional[int] = None
    photo1_found: bool = False
    photo2_id: str
    photo2_ratio: Optional[float] = None
    photo2_votes: Optional[int] = None
    photo2_rank: Optional[int] = None
    photo2_found: bool = False
    winner_id: str
    is_photo1_winner: bool
    timestamp: str
    user_id: str
    
    @classmethod
    def create(cls, user_id: str, turbo_data: Dict[str, Any]) -> 'TurboHistory':
        """Crée une nouvelle entrée d'historique turbo"""
        turbo_id = f"{turbo_data['challenge_id']}_{turbo_data['photo1_id']}_{turbo_data['photo2_id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        history_entry = cls(
            id=turbo_id,
            user_id=user_id,
            timestamp=datetime.now().isoformat(),
            **turbo_data
        )
        
        return history_entry
    
    def save(self) -> bool:
        """Sauvegarde l'entrée turbo"""
        turbo_data = {
            'challenge_id': self.challenge_id,
            'challenge_title': self.challenge_title,
            'time_left': self.time_left,
            'algorithm': self.algorithm,
            'strategy_description': self.strategy_description,
            'success': self.success,
            'photo1_id': self.photo1_id,
            'photo1_ratio': self.photo1_ratio,
            'photo1_votes': self.photo1_votes,
            'photo1_rank': self.photo1_rank,
            'photo1_found': self.photo1_found,
            'photo2_id': self.photo2_id,
            'photo2_ratio': self.photo2_ratio,
            'photo2_votes': self.photo2_votes,
            'photo2_rank': self.photo2_rank,
            'photo2_found': self.photo2_found,
            'winner_id': self.winner_id,
            'is_photo1_winner': self.is_photo1_winner,
            'timestamp': self.timestamp
        }
        
        return config_manager.save_turbo_history(self.user_id, turbo_data)
    
    @classmethod
    def get_user_history(cls, user_id: str, limit: Optional[int] = None) -> List['TurboHistory']:
        """Récupère l'historique turbo d'un utilisateur"""
        history_data = config_manager.get_turbo_history(user_id, limit)
        
        history_entries = []
        for entry in history_data:
            # Reconstruire l'ID à partir des données
            turbo_id = f"{entry['challenge_id']}_{entry['photo1']['id']}_{entry['photo2']['id']}_{entry['timestamp']}"
            
            history_entry = cls(
                id=turbo_id,
                user_id=user_id,
                challenge_id=entry['challenge_id'],
                challenge_title=entry['challenge_title'],
                time_left=entry['time_left'],
                algorithm=entry['algorithm'],
                strategy_description=entry['strategy_description'],
                success=entry['success'],
                photo1_id=entry['photo1']['id'],
                photo1_ratio=entry['photo1']['ratio'],
                photo1_votes=entry['photo1']['votes'],
                photo1_rank=entry['photo1']['rank'],
                photo1_found=entry['photo1']['found'],
                photo2_id=entry['photo2']['id'],
                photo2_ratio=entry['photo2']['ratio'],
                photo2_votes=entry['photo2']['votes'],
                photo2_rank=entry['photo2']['rank'],
                photo2_found=entry['photo2']['found'],
                winner_id=entry['winner']['id'],
                is_photo1_winner=entry['winner']['is_photo1'],
                timestamp=entry['timestamp']
            )
            
            history_entries.append(history_entry)
        
        return history_entries


class ProcessStatus(BaseModel):
    """Modèle pour le suivi des processus"""
    process_id: str
    user_id: str
    status: str
    command: Optional[str] = ""
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    
    def save(self) -> bool:
        """Sauvegarde le statut du processus"""
        return config_manager.save_process_status(
            self.user_id, 
            self.process_id, 
            self.status, 
            self.command or ""
        )