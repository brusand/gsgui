"""
Configuration Manager Service - Persistance fichier .ini comme dans gsui.py
Remplace la base de données pour les plateformes sans BD
"""

import os
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from configobj import ConfigObj
from threading import RLock  # Reentrant Lock pour éviter deadlocks
import uuid

# Import centralized paths - ABSOLUTE PATHS regardless of CWD
from app.utils.paths import GSGUI_INI_PATH_STR, STRATEGIES_INI_PATH_STR

logger = logging.getLogger(__name__)

# Use absolute paths from centralized paths module
DEFAULT_GSGUI_INI = GSGUI_INI_PATH_STR
DEFAULT_STRATEGIES_INI = STRATEGIES_INI_PATH_STR


class ConfigManager:
    """
    Gestionnaire de configuration utilisant les fichiers .ini
    Compatible avec le format de gsui.py pour une migration transparente
    """

    def __init__(self, config_file: str = None, strategies_file: str = None):
        self.config_file = config_file if config_file is not None else DEFAULT_GSGUI_INI
        self.strategies_file = strategies_file if strategies_file is not None else DEFAULT_STRATEGIES_INI
        self._lock = RLock()  # Reentrant Lock pour thread safety sans deadlocks

        # DEBUG: Afficher les chemins absolus réels utilisés
        import os
        abs_config = os.path.abspath(self.config_file)
        abs_strategies = os.path.abspath(self.strategies_file)
        cwd = os.getcwd()
        logger.info(f"📂 ConfigManager paths:")
        logger.info(f"   CWD: {cwd}")
        logger.info(f"   gsgui.ini: {abs_config}")
        logger.info(f"   strategies.ini: {abs_strategies}")
        logger.info(f"   File exists: {os.path.exists(abs_config)}")

        # Chargement initial
        self._load_configs()
        logger.info(f"✅ ConfigManager initialized")
    
    def _load_configs(self):
        """Charge les fichiers de configuration"""
        try:
            # DEBUG: Vérifier le chemin absolu au moment du chargement
            abs_path = os.path.abspath(self.config_file)
            logger.info(f"📖 Loading config from: {abs_path} (exists: {os.path.exists(abs_path)})")

            # Configuration principale (gsgui.ini)
            if os.path.exists(self.config_file):
                self.config = ConfigObj(self.config_file, encoding='utf-8')
            else:
                self.config = ConfigObj(self.config_file, encoding='utf-8')
                self._create_default_config()
            
            # Stratégies (strategies.ini)
            if os.path.exists(self.strategies_file):
                self.strategies = ConfigObj(self.strategies_file, encoding='utf-8')
            else:
                self.strategies = ConfigObj(self.strategies_file, encoding='utf-8')
                self._create_default_strategies()
            
            # S'assurer que l'encodage UTF-8 est fixé
            self.config.encoding = 'utf-8'
            self.strategies.encoding = 'utf-8'
            
        except Exception as e:
            logger.error(f"Error loading configs: {e}")
            # Créer des configs par défaut en cas d'erreur
            self.config = ConfigObj(self.config_file, encoding='utf-8')
            self.strategies = ConfigObj(self.strategies_file, encoding='utf-8')
            self._create_default_config()
            self._create_default_strategies()
    
    def _create_default_config(self):
        """Crée une configuration par défaut"""
        self.config['version'] = '1.0.0'
        self.config['player'] = 'default_user'
        self.config['host'] = ""
        self.config['challenge'] = ""
        
        # Section players vide au début
        self.config['players'] = {}
        
        self._save_config()
    
    def _create_default_strategies(self):
        """Crée des stratégies par défaut"""
        self.strategies['end4'] = {
            'description': 'Stratégie conservative - 4m - votes répartis',
            '0': 'vote, end-4m0s, 70',
            '1': 'vote, end-3m0s, 40',
            '2': 'vote, end-2m0s, 40',
            '3': 'vote, end-1m0s, 40',
            '4': 'vote, end-0m30s, 20'
        }
        
        self.strategies['fill'] = {
            'description': 'Stratégie rapide - maintenant',
            '0': 'vote, now, 70'
        }
        
        self._save_strategies()
    
    def _save_config(self):
        """Sauvegarde la configuration principale"""
        with self._lock:
            try:
                # DEBUG: Vérifier le chemin absolu au moment de la sauvegarde
                abs_path = os.path.abspath(self.config_file)
                logger.info(f"💾 Saving config to: {abs_path}")
                self.config.write()
                logger.debug(f"Configuration saved to {self.config_file}")
            except Exception as e:
                logger.error(f"Error saving config: {e}")
    
    def _save_strategies(self):
        """Sauvegarde les stratégies"""
        with self._lock:
            try:
                self.strategies.write()
                logger.debug(f"Strategies saved to {self.strategies_file}")
            except Exception as e:
                logger.error(f"Error saving strategies: {e}")
    
    # === USER MANAGEMENT ===
    
    def create_user(self, user_id: str, user_data: Dict[str, Any]) -> bool:
        """Crée un nouvel utilisateur"""
        try:
            if 'players' not in self.config:
                self.config['players'] = {}
            
            # Données utilisateur avec valeurs par défaut de gsui.py
            user_section = {
                'user_name': user_data.get('user_name', ''),
                'xtoken': user_data.get('xtoken', ''),
                'turbo_algorithm': user_data.get('turbo_algorithm', 'hybrid'),
                'auto_optimize_turbo': user_data.get('auto_optimize_turbo', True),
                'created_at': datetime.now().isoformat()
            }
            
            # Sections comme dans gsui.py
            user_section['challenges'] = {}
            user_section['process'] = {}
            user_section['cmdes'] = {}
            
            self.config['players'][user_id] = user_section
            self._save_config()
            
            logger.info(f"✅ User {user_id} created")
            return True
            
        except Exception as e:
            logger.error(f"Error creating user {user_id}: {e}")
            return False
    
    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Récupère un utilisateur"""
        try:
            users = self.config.get('players', {})
            return users.get(user_id)
        except Exception as e:
            logger.error(f"Error getting user {user_id}: {e}")
            return None
    
    def get_user_section(self, user_id: str, section_name: str) -> Optional[Dict[str, Any]]:
        """Récupère une section spécifique d'un utilisateur"""
        try:
            users = self.config.get('players', {})
            user_data = users.get(user_id, {})
            return user_data.get(section_name, {})
        except Exception as e:
            logger.error(f"Error getting user section {user_id}.{section_name}: {e}")
            return {}
    
    def update_user(self, user_id: str, updates: Dict[str, Any]) -> bool:
        """Met à jour un utilisateur"""
        try:
            if 'players' not in self.config or user_id not in self.config['players']:
                return False
            
            # Mise à jour des champs
            for key, value in updates.items():
                self.config['players'][user_id][key] = value
            
            self.config['players'][user_id]['updated_at'] = datetime.now().isoformat()
            self._save_config()
            
            logger.debug(f"User {user_id} updated")
            return True
            
        except Exception as e:
            logger.error(f"Error updating user {user_id}: {e}")
            return False
    
    def list_users(self) -> List[str]:
        """Liste tous les utilisateurs"""
        try:
            return list(self.config.get('players', {}).keys())
        except Exception as e:
            logger.error(f"Error listing users: {e}")
            return []
    
    # === CHALLENGE MANAGEMENT ===
    
    def save_user_challenge(self, user_id: str, challenge_id: str, challenge_data: Dict[str, Any]) -> bool:
        """Sauvegarde un challenge pour un utilisateur"""
        # LOCK GLOBAL pour éviter race condition entre les auto-refresh de différents profils
        # qui s'exécutent en parallèle et écrasent les modifications des autres
        with self._lock:
            try:
                # IMPORTANT: Recharger le config depuis le fichier pour avoir les dernières scheduled_strategies
                # Car le strategy_scheduler peut avoir modifié le fichier directement
                self._load_configs()

                if user_id not in self.config.get('players', {}):
                    return False

                if 'challenges' not in self.config['players'][user_id]:
                    self.config['players'][user_id]['challenges'] = {}

                # DEBUG: Vérifier scheduled_strategies AVANT toute modification
                scheduled_strategies = self.config['players'][user_id].get('scheduled_strategies', {})
                logger.info(f"🔍 [save_user_challenge] BEFORE save - scheduled_strategies keys for {user_id}: {list(scheduled_strategies.keys())}")

                # Déterminer le strategy_name à utiliser (priorité: scheduled_strategies > existant > fourni > vide)
                strategy_name = ''

                # 1. Vérifier si une stratégie est schedulée pour ce challenge

                # Debug: afficher les clés disponibles
                logger.debug(f"Looking for challenge {challenge_id} (type: {type(challenge_id)})")
                logger.debug(f"Scheduled strategies keys: {list(scheduled_strategies.keys())}")

                # Essayer avec le challenge_id tel quel et aussi en convertissant
                if challenge_id in scheduled_strategies:
                    strategy_name = scheduled_strategies[challenge_id].get('strategy_name', '')
                    logger.debug(f"Found strategy in scheduled_strategies: '{strategy_name}'")
                elif str(challenge_id) in scheduled_strategies:
                    strategy_name = scheduled_strategies[str(challenge_id)].get('strategy_name', '')
                    logger.debug(f"Found strategy in scheduled_strategies (str): '{strategy_name}'")

                # 2. Sinon, préserver le strategy_name existant si le challenge existe déjà
                if not strategy_name and challenge_id in self.config['players'][user_id]['challenges']:
                    strategy_name = self.config['players'][user_id]['challenges'][challenge_id].get('strategy_name', '')
                    logger.debug(f"Found existing strategy in challenges: '{strategy_name}'")

                # 3. Sinon, utiliser celui fourni dans challenge_data
                if not strategy_name:
                    strategy_name = challenge_data.get('selected_strategy', '')
                    if strategy_name:
                        logger.debug(f"Using strategy from challenge_data: '{strategy_name}'")

                # Sauvegarder avec le format de gsui.py
                challenge_section = {
                    'strategy_name': strategy_name,
                    'challenge_title': challenge_data.get('title', ''),
                    'scheduled_at': challenge_data.get('scheduled_at', datetime.now().isoformat()),
                    'status': challenge_data.get('status', ''),
                    'votes': challenge_data.get('votes', 0),
                    'rank': challenge_data.get('rank', 0)
                }

                self.config['players'][user_id]['challenges'][challenge_id] = challenge_section

                # DEBUG: Vérifier scheduled_strategies AVANT write
                scheduled_strategies_before_write = self.config['players'][user_id].get('scheduled_strategies', {})
                logger.info(f"🔍 [save_user_challenge] BEFORE write - scheduled_strategies keys: {list(scheduled_strategies_before_write.keys())}")

                self._save_config()

                # DEBUG: Vérifier scheduled_strategies APRÈS write (relire le fichier)
                self._load_configs()
                scheduled_strategies_after_write = self.config['players'][user_id].get('scheduled_strategies', {})
                logger.info(f"🔍 [save_user_challenge] AFTER write - scheduled_strategies keys: {list(scheduled_strategies_after_write.keys())}")

                logger.debug(f"Challenge {challenge_id} saved for user {user_id} with strategy '{strategy_name}'")
                return True

            except Exception as e:
                logger.error(f"Error saving challenge {challenge_id} for user {user_id}: {e}")
                return False
    
    def get_user_challenges(self, user_id: str) -> Dict[str, Any]:
        """Récupère tous les challenges d'un utilisateur"""
        try:
            user = self.get_user(user_id)
            if user:
                return user.get('challenges', {})
            return {}
        except Exception as e:
            logger.error(f"Error getting challenges for user {user_id}: {e}")
            return {}
    
    def update_challenge_status(self, user_id: str, challenge_id: str, status: str, additional_data: Optional[Dict] = None) -> bool:
        """Met à jour le statut d'un challenge"""
        try:
            if user_id not in self.config.get('players', {}):
                return False
            
            challenges = self.config['players'][user_id].get('challenges', {})
            if challenge_id in challenges:
                challenges[challenge_id]['status'] = status
                challenges[challenge_id]['updated_at'] = datetime.now().isoformat()
                
                if additional_data:
                    challenges[challenge_id].update(additional_data)
                
                self._save_config()
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error updating challenge status: {e}")
            return False
    
    # === STRATEGY MANAGEMENT ===
    
    def get_strategy(self, strategy_name: str) -> Optional[Dict[str, Any]]:
        """Récupère une stratégie"""
        try:
            return self.strategies.get(strategy_name)
        except Exception as e:
            logger.error(f"Error getting strategy {strategy_name}: {e}")
            return None
    
    def list_strategies(self) -> Dict[str, Any]:
        """Liste toutes les stratégies"""
        try:
            return dict(self.strategies)
        except Exception as e:
            logger.error(f"Error listing strategies: {e}")
            return {}
    
    def create_strategy(self, strategy_name: str, strategy_config: Dict[str, Any]) -> bool:
        """Crée une nouvelle stratégie"""
        try:
            self.strategies[strategy_name] = strategy_config
            self._save_strategies()
            
            logger.info(f"✅ Strategy {strategy_name} created")
            return True
            
        except Exception as e:
            logger.error(f"Error creating strategy {strategy_name}: {e}")
            return False
    
    # === TURBO HISTORY ===
    
    def save_turbo_history(self, user_id: str, turbo_data: Dict[str, Any]) -> bool:
        """Sauvegarde l'historique turbo comme dans gsui.py"""
        try:
            if user_id not in self.config.get('players', {}):
                return False
            
            # Créer la section turbo_history si elle n'existe pas
            if 'turbo_history' not in self.config:
                self.config['turbo_history'] = {}
            
            if user_id not in self.config['turbo_history']:
                self.config['turbo_history'][user_id] = {}
            
            # ID unique pour l'entrée turbo (format gsui.py)
            challenge_id = turbo_data['challenge_id']
            photo1_id = turbo_data['photo1_id']
            photo2_id = turbo_data['photo2_id']
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            turbo_id = f"{challenge_id}_{photo1_id}_{photo2_id}_{timestamp}"
            
            # Format complet comme dans gsui.py
            turbo_entry = {
                'timestamp': turbo_data.get('timestamp', datetime.now().isoformat()),
                'challenge_id': challenge_id,
                'challenge_title': turbo_data.get('challenge_title', ''),
                'time_left': turbo_data.get('time_left', ''),
                'algorithm': turbo_data.get('algorithm', 'default'),
                'strategy_description': turbo_data.get('strategy_description', ''),
                'success': turbo_data.get('success', False),
                'photo1': {
                    'id': photo1_id,
                    'ratio': turbo_data.get('photo1_ratio'),
                    'votes': turbo_data.get('photo1_votes'),
                    'rank': turbo_data.get('photo1_rank'),
                    'found': turbo_data.get('photo1_found', False)
                },
                'photo2': {
                    'id': photo2_id,
                    'ratio': turbo_data.get('photo2_ratio'),
                    'votes': turbo_data.get('photo2_votes'),
                    'rank': turbo_data.get('photo2_rank'),
                    'found': turbo_data.get('photo2_found', False)
                },
                'winner': {
                    'id': turbo_data.get('winner_id'),
                    'is_photo1': turbo_data.get('is_photo1_winner', False)
                }
            }
            
            self.config['turbo_history'][user_id][turbo_id] = turbo_entry
            self._save_config()
            
            logger.debug(f"Turbo history saved: {turbo_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving turbo history: {e}")
            return False
    
    def get_turbo_history(self, user_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Récupère l'historique turbo d'un utilisateur"""
        try:
            history = self.config.get('turbo_history', {}).get(user_id, {})
            entries = list(history.values())
            
            # Trier par timestamp (plus récent en premier)
            entries.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            
            if limit:
                entries = entries[:limit]
            
            return entries
            
        except Exception as e:
            logger.error(f"Error getting turbo history for user {user_id}: {e}")
            return []
    
    # === PROCESS TRACKING (comme dans gsui.py) ===
    
    def save_process_status(self, user_id: str, process_id: str, status: str, command: str = "") -> bool:
        """Sauvegarde le statut d'un processus"""
        try:
            if user_id not in self.config.get('players', {}):
                return False
            
            if 'process' not in self.config['players'][user_id]:
                self.config['players'][user_id]['process'] = {}
            
            if 'cmdes' not in self.config['players'][user_id]:
                self.config['players'][user_id]['cmdes'] = {}
            
            # Sauvegarder le statut et la commande (format gsui.py)
            self.config['players'][user_id]['process'][process_id] = status
            
            if command:
                self.config['players'][user_id]['cmdes'][process_id] = command
            
            self._save_config()
            return True
            
        except Exception as e:
            logger.error(f"Error saving process status: {e}")
            return False
    
    def get_user_processes(self, user_id: str) -> Dict[str, str]:
        """Récupère tous les processus d'un utilisateur"""
        try:
            user = self.get_user(user_id)
            if user:
                return user.get('process', {})
            return {}
        except Exception as e:
            logger.error(f"Error getting processes for user {user_id}: {e}")
            return {}
    
    # === USER MANAGEMENT METHODS ===
    
    def list_users(self) -> List[str]:
        """Retourne la liste des IDs utilisateur disponibles"""
        try:
            players = self.config.get('players', {})
            return list(players.keys())
        except Exception as e:
            logger.error(f"Error listing users: {e}")
            return []
    
    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Récupère les informations d'un utilisateur"""
        try:
            players = self.config.get('players', {})
            return players.get(user_id)
        except Exception as e:
            logger.error(f"Error getting user {user_id}: {e}")
            return None
    
    def create_user(self, user_id: str, user_data: Dict[str, Any]) -> bool:
        """Crée un nouvel utilisateur"""
        try:
            with self._lock:
                if 'players' not in self.config:
                    self.config['players'] = {}
                
                self.config['players'][user_id] = user_data
                self.config.write()
                logger.info(f"✅ User {user_id} created")
                return True
        except Exception as e:
            logger.error(f"Error creating user {user_id}: {e}")
            return False
    
    def update_user(self, user_id: str, updates: Dict[str, Any]) -> bool:
        """Met à jour un utilisateur existant (mise à jour partielle des clés de premier niveau)"""
        try:
            with self._lock:
                players = self.config.get('players', {})
                if user_id not in players:
                    logger.warning(f"User {user_id} not found for update")
                    return False

                # DEBUG: Vérifier scheduled_strategies AVANT update
                scheduled_before = players[user_id].get('scheduled_strategies', {})
                logger.info(f"🔍 [update_user] BEFORE update - scheduled_strategies keys for {user_id}: {list(scheduled_before.keys())}")

                # Mise à jour partielle : ne modifie que les clés présentes dans updates
                for key, value in updates.items():
                    players[user_id][key] = value

                # DEBUG: Vérifier scheduled_strategies APRÈS update mais AVANT write
                scheduled_after_update = players[user_id].get('scheduled_strategies', {})
                logger.info(f"🔍 [update_user] AFTER update, BEFORE write - scheduled_strategies keys: {list(scheduled_after_update.keys())}")

                self.config.write()

                # DEBUG: Vérifier scheduled_strategies APRÈS write
                self._load_configs()
                scheduled_after_write = self.config['players'][user_id].get('scheduled_strategies', {})
                logger.info(f"🔍 [update_user] AFTER write - scheduled_strategies keys: {list(scheduled_after_write.keys())}")

                logger.debug(f"✅ User {user_id} updated with keys: {list(updates.keys())}")
                return True
        except Exception as e:
            logger.error(f"Error updating user {user_id}: {e}")
            return False

    def update_user_section(self, user_id: str, section_name: str, section_data: Dict[str, Any]) -> bool:
        """Met à jour une section spécifique d'un utilisateur (ex: scheduled_strategies, turbo_history)"""
        try:
            with self._lock:
                players = self.config.get('players', {})
                if user_id not in players:
                    logger.warning(f"User {user_id} not found for section update")
                    return False

                # Remplacer complètement la section
                players[user_id][section_name] = section_data

                self.config.write()
                logger.debug(f"✅ User {user_id} section '{section_name}' updated")
                return True
        except Exception as e:
            logger.error(f"Error updating user {user_id} section {section_name}: {e}")
            return False

    def get_user_challenges(self, user_id: str) -> Dict[str, Any]:
        """Récupère les challenges/stratégies d'un utilisateur"""
        try:
            players = self.config.get('players', {})
            user = players.get(user_id, {})
            return user.get('scheduled_strategies', {})
        except Exception as e:
            logger.error(f"Error getting challenges for user {user_id}: {e}")
            return {}
    
    def get_turbo_history(self, user_id: str) -> List[Dict[str, Any]]:
        """Récupère l'historique turbo d'un utilisateur"""
        try:
            turbo_history = self.config.get('turbo_history', {})
            user_history = turbo_history.get(user_id, {})
            
            # Convertir en liste
            history_list = []
            for turbo_id, turbo_data in user_history.items():
                turbo_entry = dict(turbo_data)
                turbo_entry['turbo_id'] = turbo_id
                history_list.append(turbo_entry)
            
            return sorted(history_list, key=lambda x: x.get('timestamp', ''), reverse=True)
        except Exception as e:
            logger.error(f"Error getting turbo history for user {user_id}: {e}")
            return []

    # === UTILITY METHODS ===
    
    def reload_configs(self):
        """Recharge les configurations depuis les fichiers"""
        self._load_configs()
        logger.debug("Configurations reloaded")
    
    def backup_configs(self, backup_suffix: Optional[str] = None) -> bool:
        """Crée une sauvegarde des fichiers de configuration"""
        try:
            if not backup_suffix:
                backup_suffix = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            import shutil
            
            # Sauvegarder gsgui.ini
            if os.path.exists(self.config_file):
                backup_config = f"{self.config_file}.backup_{backup_suffix}"
                shutil.copy2(self.config_file, backup_config)
            
            # Sauvegarder strategies.ini
            if os.path.exists(self.strategies_file):
                backup_strategies = f"{self.strategies_file}.backup_{backup_suffix}"
                shutil.copy2(self.strategies_file, backup_strategies)
            
            logger.info(f"✅ Configurations backed up with suffix {backup_suffix}")
            return True
            
        except Exception as e:
            logger.error(f"Error backing up configurations: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne des statistiques sur les configurations"""
        try:
            users_count = len(self.config.get('players', {}))
            strategies_count = len(self.strategies)
            
            # Compter l'historique turbo total
            turbo_history_count = 0
            turbo_history = self.config.get('turbo_history', {})
            for user_history in turbo_history.values():
                turbo_history_count += len(user_history)
            
            return {
                'users_count': users_count,
                'strategies_count': strategies_count,
                'turbo_history_count': turbo_history_count,
                'config_file': self.config_file,
                'strategies_file': self.strategies_file,
                'last_reload': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {}


# Instance globale du gestionnaire de configuration
config_manager = ConfigManager()