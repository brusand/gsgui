"""
GuruShots Data Collector - Version utilisant l'API backend
"""

import os
import sys
import json
import time
import logging
import requests
import sqlite3
import schedule
from datetime import datetime
from dotenv import load_dotenv


class GuruShotsCollectorBackend:
    def __init__(self, config_path=None):
        """Initialise le collecteur avec la configuration"""
        if config_path:
            load_dotenv(config_path)
        else:
            # Chercher collector.env dans le répertoire parent (gsgui/)
            script_dir = os.path.dirname(os.path.abspath(__file__))
            parent_dir = os.path.dirname(script_dir)
            collector_env = os.path.join(parent_dir, 'collector.env')

            if os.path.exists(collector_env):
                load_dotenv(collector_env)
            else:
                load_dotenv()  # Fallback sur .env

        # Configuration de la base de données
        self.db_path = os.getenv('DATABASE_PATH', 'data/gurushots_data.db')
        self.db_path_local_fallback = 'data/gurushots_data_local.db'
        # Résoudre les chemins relatifs depuis la racine du projet (indépendant du CWD)
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if not os.path.isabs(self.db_path):
            self.db_path = os.path.join(project_root, self.db_path)
        if not os.path.isabs(self.db_path_local_fallback):
            self.db_path_local_fallback = os.path.join(project_root, self.db_path_local_fallback)

        # Configuration de l'API Backend (au lieu de l'API GuruShots directe)
        self.backend_api_url = "http://calounette.ddns.net/api/v1"
        self.profile_name = "bruno"

        # Configuration de collecte
        self.collection_interval = int(os.getenv('COLLECTION_INTERVAL_MINUTES', 30))

        # Challenges à suivre
        challenge_ids_str = os.getenv('CHALLENGE_IDS', '')
        self.challenge_ids = [x.strip() for x in challenge_ids_str.split(',') if x.strip()]

        # Configuration des logs
        log_level = os.getenv('LOG_LEVEL', 'INFO')
        log_file = os.getenv('LOG_FILE', 'gurushots_collector.log')

        logging.basicConfig(
            level=getattr(logging, log_level),
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)

        # Vérifier la disponibilité du stockage réseau
        self._check_network_storage()

        # Initialiser la base de données
        self.init_database()

    def _check_network_storage(self):
        """Vérifie la disponibilité du stockage réseau"""
        try:
            network_dir = os.path.dirname(self.db_path)
            if network_dir and not os.path.exists(network_dir):
                self.logger.warning(f"Stockage réseau non disponible: {network_dir}")
                self.logger.warning(f"Utilisation du stockage local: {self.db_path_local_fallback}")
                self.db_path = self.db_path_local_fallback
                return False

            # Tester l'écriture
            if network_dir:
                test_file = os.path.join(network_dir, '.write_test')
                with open(test_file, 'w') as f:
                    f.write('test')
                os.remove(test_file)

            self.logger.info(f"Stockage réseau accessible: {self.db_path}")
            return True

        except Exception as e:
            self.logger.warning(f"Problème stockage réseau: {e}")
            self.logger.warning(f"Basculement vers stockage local: {self.db_path_local_fallback}")
            self.db_path = self.db_path_local_fallback
            return False

    def init_database(self):
        """Crée la structure de la base de données SQLite"""
        self.logger.info(f"Initialisation de la base de données : {self.db_path}")

        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Table des challenges
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS challenges (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                url TEXT,
                status TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Table des snapshots
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                challenge_id TEXT,
                timestamp DATETIME NOT NULL,
                total_participants INTEGER,
                FOREIGN KEY (challenge_id) REFERENCES challenges(id)
            )
        ''')

        # Table des participants
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS members (
                id TEXT PRIMARY KEY,
                name TEXT,
                user_name TEXT,
                country_code TEXT,
                member_status INTEGER,
                member_status_name TEXT,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Table des positions globales
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS participant_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_id INTEGER,
                member_id TEXT,
                total_votes INTEGER,
                total_rank INTEGER,
                level INTEGER,
                level_name TEXT,
                level_rank INTEGER,
                percent REAL,
                guru_picks INTEGER,
                following BOOLEAN DEFAULT TRUE,
                FOREIGN KEY (snapshot_id) REFERENCES snapshots(id),
                FOREIGN KEY (member_id) REFERENCES members(id)
            )
        ''')

        # Index pour optimiser les requêtes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_snapshots_challenge_time ON snapshots(challenge_id, timestamp)')
        cursor.execute(
            'CREATE INDEX IF NOT EXISTS idx_participant_snapshots_snapshot ON participant_snapshots(snapshot_id)')

        conn.commit()
        conn.close()

        self.logger.info("Base de données initialisée avec succès")

    def get_challenges_from_backend(self):
        """Récupère les challenges depuis l'API backend"""
        try:
            self.logger.info(f"Récupération des challenges depuis l'API backend...")

            response = requests.get(
                f"{self.backend_api_url}/challenges/",
                params={"profile_name": self.profile_name},
                timeout=30
            )
            response.raise_for_status()

            data = response.json()
            self.logger.info(f"Données reçues de l'API backend")

            return data

        except requests.RequestException as e:
            self.logger.error(f"Erreur lors de la requête API backend: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Erreur inattendue API backend: {e}")
            return None

    def save_snapshot_from_backend(self, data):
        """Sauvegarde un snapshot depuis les données de l'API backend"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            timestamp = datetime.now()

            # Extraire les challenges des données
            challenges_list = []
            if isinstance(data, dict) and 'challenges' in data:
                challenges_list = data['challenges']
            elif isinstance(data, list):
                challenges_list = data

            self.logger.info(f"Traitement de {len(challenges_list)} challenges")

            for challenge in challenges_list:
                if not isinstance(challenge, dict):
                    continue

                challenge_id = str(challenge.get('id', ''))
                if not challenge_id:
                    continue

                # Sauvegarder les infos du challenge
                cursor.execute('''
                    INSERT OR REPLACE INTO challenges (id, title, url, status)
                    VALUES (?, ?, ?, ?)
                ''', (
                    challenge_id,
                    challenge.get('title', f'Challenge {challenge_id}'),
                    challenge.get('url', ''),
                    challenge.get('status', 'active')
                ))

                # Créer le snapshot pour ce challenge
                cursor.execute('''
                    INSERT INTO snapshots (challenge_id, timestamp, total_participants)
                    VALUES (?, ?, ?)
                ''', (challenge_id, timestamp, 1))  # 1 participant = Bruno

                snapshot_id = cursor.lastrowid

                # Sauvegarder les infos du membre (Bruno)
                cursor.execute('''
                    INSERT OR REPLACE INTO members 
                    (id, name, user_name, country_code, member_status, member_status_name, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    self.profile_name,
                    self.profile_name,
                    self.profile_name,
                    'FR',  # Assumé
                    1,
                    'USER',
                    timestamp
                ))

                # Sauvegarder la position du participant
                cursor.execute('''
                    INSERT INTO participant_snapshots 
                    (snapshot_id, member_id, total_votes, total_rank, level, level_name, 
                     level_rank, percent, guru_picks, following)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    snapshot_id,
                    self.profile_name,
                    challenge.get('votes', 0),
                    challenge.get('rank', 0),
                    challenge.get('level', 1),
                    challenge.get('level_name', 'ROOKIE'),
                    challenge.get('rank', 0),
                    0.0,  # percent
                    0,  # guru_picks
                    True  # following
                ))

            conn.commit()
            self.logger.info(f"Snapshot sauvegardé avec {len(challenges_list)} challenges")

        except Exception as e:
            conn.rollback()
            self.logger.error(f"Erreur lors de la sauvegarde: {e}")
            raise
        finally:
            conn.close()

    def collect_all_challenges(self):
        """Collecte les données de tous les challenges"""
        self.logger.info("Début de la collecte depuis l'API backend")

        # Récupérer les données depuis l'API backend
        data = self.get_challenges_from_backend()

        if data:
            # Sauvegarder les données
            self.save_snapshot_from_backend(data)
            self.logger.info("Collecte terminée avec succès")
        else:
            self.logger.error("Aucune donnée récupérée depuis l'API backend")

    def start_scheduler(self):
        """Démarre le collecteur en mode schedulé"""
        self.logger.info(f"Démarrage du scheduler - collecte toutes les {self.collection_interval} minutes")

        # Programmer la collecte
        schedule.every(self.collection_interval).minutes.do(self.collect_all_challenges)

        # Collecte initiale
        self.collect_all_challenges()

        # Boucle principale
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)
        except KeyboardInterrupt:
            self.logger.info("Arrêt du collecteur demandé par l'utilisateur")
        except Exception as e:
            self.logger.error(f"Erreur dans le scheduler: {e}")


def main():
    """Fonction principale"""
    import argparse

    parser = argparse.ArgumentParser(description='GuruShots Data Collector (Backend API)')
    parser.add_argument('--config', help='Chemin vers le fichier de configuration')
    parser.add_argument('--daemon', action='store_true', help='Mode daemon (collecte continue)')

    args = parser.parse_args()

    # Initialiser le collecteur
    collector = GuruShotsCollectorBackend(args.config)

    if args.daemon:
        # Mode daemon
        collector.start_scheduler()
    else:
        # Collecte unique
        collector.collect_all_challenges()


if __name__ == "__main__":
    main()