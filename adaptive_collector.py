#!/usr/bin/env python3
"""
GuruShots Adaptive Collection Scheduler
Logique de collecte adaptative avec stratégies configurables
"""

import asyncio
import aiohttp
import sqlite3
import json
import logging
import os
import time
import configparser
import re
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

# APScheduler imports
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class CollectionStrategy:
    """Stratégie de collecte"""
    name: str
    description: str
    action: str
    interval: str
    from_time: str
    to_time: str

@dataclass
class CollectionConfig:
    """Configuration du collector adaptatif"""
    database_path: str
    bruno_token: str
    strategies_file: str = "collection_strategies.ini"
    
    def __post_init__(self):
        os.makedirs(os.path.dirname(self.database_path), exist_ok=True)

class AdaptiveCollectionScheduler:
    """Scheduler avec collecte adaptative par stratégies"""
    
    def __init__(self, config: CollectionConfig):
        self.config = config
        self.db_path = config.database_path
        self.bruno_token = config.bruno_token
        self.strategies_file = config.strategies_file
        
        # Configuration APScheduler
        jobstores = {'default': MemoryJobStore()}
        executors = {'default': AsyncIOExecutor()}
        job_defaults = {'coalesce': False, 'max_instances': 5}
        
        self.scheduler = AsyncIOScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone=timezone.utc
        )
        
        self._running = False
        self.strategies: List[CollectionStrategy] = []
        self.active_challenges: Dict[str, Dict] = {}
        
        # Charger les stratégies
        self.load_strategies()
        
        # Initialiser la base de données (même schéma qu'avant)
        self.init_database()
        
        logger.info("🎯 Adaptive Collection Scheduler initialized")
    
    def parse_time_offset(self, time_str: str) -> int:
        """Parse un offset de temps comme '1h:30m:45s' ou '1h30m' (du backend)"""
        if time_str == "now":
            return 0
            
        try:
            total_seconds = 0
            
            # Support format 1h:30m:45s
            time_str = time_str.replace(':', '')
            
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
        except Exception as e:
            logger.error(f"Error parsing time offset '{time_str}': {e}")
            return None
    
    def parse_interval_to_seconds(self, interval_str: str) -> int:
        """Parse l'intervalle comme 'next-15m', 'next-5m', etc."""
        if not interval_str.startswith('next-'):
            return None
            
        time_part = interval_str[5:]  # Enlever 'next-'
        return self.parse_time_offset(time_part)
    
    def load_strategies(self):
        """Charger les stratégies depuis le fichier de configuration"""
        if not os.path.exists(self.strategies_file):
            logger.error(f"❌ Strategies file not found: {self.strategies_file}")
            return
        
        config = configparser.ConfigParser()
        config.read(self.strategies_file)
        
        self.strategies = []
        
        for section_name in config.sections():
            section = config[section_name]
            description = section.get('description', '').strip('"')
            
            # Parse la ligne d'action (0="collecte, next-15m, now, 1h:0m:0s")
            if '0' in section:
                action_line = section['0'].strip('"')
                parts = [part.strip() for part in action_line.split(',')]
                
                if len(parts) == 4:
                    action, interval, from_time, to_time = parts
                    
                    strategy = CollectionStrategy(
                        name=section_name,
                        description=description,
                        action=action,
                        interval=interval,
                        from_time=from_time,
                        to_time=to_time
                    )
                    
                    self.strategies.append(strategy)
                    logger.info(f"✅ Loaded strategy: {section_name}")
        
        logger.info(f"📋 Loaded {len(self.strategies)} collection strategies")
    
    def find_active_strategy(self, seconds_to_end: int) -> Optional[CollectionStrategy]:
        """Trouver la stratégie active selon le temps restant"""
        for strategy in self.strategies:
            from_seconds = self.parse_time_offset(strategy.from_time)
            to_seconds = self.parse_time_offset(strategy.to_time)
            
            if from_seconds is None or to_seconds is None:
                continue
            
            # Logique: from_time >= seconds_to_end > to_time
            if strategy.from_time == "now":
                # Stratégie depuis maintenant
                if seconds_to_end >= to_seconds:
                    return strategy
            else:
                # Stratégie dans une plage
                if from_seconds >= seconds_to_end > to_seconds:
                    return strategy
        
        return None
    
    def init_database(self):
        """Initialiser la base de données (même schéma qu'avant)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Tables identiques
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS challenges (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                url TEXT,
                status TEXT,
                start_time TIMESTAMP,
                end_time TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                challenge_id TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                seconds_to_end INTEGER NOT NULL,
                total_participants INTEGER,
                collection_phase TEXT,
                active_strategy TEXT, -- NOUVEAU: stratégie utilisée
                next_collection_in INTEGER, -- NOUVEAU: prochaine collecte dans X secondes
                scheduled_time TIMESTAMP,
                FOREIGN KEY (challenge_id) REFERENCES challenges (id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS members (
                id TEXT PRIMARY KEY,
                username TEXT,
                name TEXT,
                country_code TEXT,
                member_status INTEGER,
                member_status_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS participant_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_id INTEGER NOT NULL,
                member_id TEXT NOT NULL,
                total_votes INTEGER NOT NULL,
                total_rank INTEGER NOT NULL,
                total_level INTEGER,
                total_level_name TEXT,
                total_percent REAL,
                photos_count INTEGER,
                guru_picks_count INTEGER DEFAULT 0,
                following_status BOOLEAN DEFAULT TRUE,
                FOREIGN KEY (snapshot_id) REFERENCES snapshots (id),
                FOREIGN KEY (member_id) REFERENCES members (id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS photo_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                participant_snapshot_id INTEGER NOT NULL,
                photo_id TEXT NOT NULL,
                votes INTEGER NOT NULL,
                rank INTEGER NOT NULL,
                boost_timestamp INTEGER,
                turbo_timestamp INTEGER,
                guru_pick BOOLEAN DEFAULT FALSE,
                event_id TEXT,
                is_new_submit BOOLEAN DEFAULT FALSE,
                is_swapped BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (participant_snapshot_id) REFERENCES participant_snapshots (id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_id INTEGER NOT NULL,
                member_id TEXT NOT NULL,
                photo_id TEXT,
                event_type TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                seconds_to_end INTEGER,
                metadata TEXT,
                FOREIGN KEY (snapshot_id) REFERENCES snapshots (id),
                FOREIGN KEY (member_id) REFERENCES members (id)
            )
        ''')
        
        # Index identiques
        indexes = [
            'CREATE INDEX IF NOT EXISTS idx_snapshots_challenge_time ON snapshots (challenge_id, timestamp)',
            'CREATE INDEX IF NOT EXISTS idx_snapshots_seconds_to_end ON snapshots (seconds_to_end)',
            'CREATE INDEX IF NOT EXISTS idx_participant_snapshots_member ON participant_snapshots (member_id, snapshot_id)',
            'CREATE INDEX IF NOT EXISTS idx_participant_snapshots_rank ON participant_snapshots (total_rank)',
            'CREATE INDEX IF NOT EXISTS idx_participant_snapshots_percent ON participant_snapshots (total_percent)',
            'CREATE INDEX IF NOT EXISTS idx_events_type_time ON events (event_type, timestamp)',
            'CREATE INDEX IF NOT EXISTS idx_events_seconds_to_end ON events (seconds_to_end)',
            'CREATE INDEX IF NOT EXISTS idx_photo_snapshots_boost ON photo_snapshots (boost_timestamp)',
            'CREATE INDEX IF NOT EXISTS idx_photo_snapshots_turbo ON photo_snapshots (turbo_timestamp)'
        ]
        
        for index_sql in indexes:
            cursor.execute(index_sql)
        
        conn.commit()
        conn.close()
        logger.info(f"✅ Database initialized: {self.db_path}")
    
    async def get_my_active_challenges(self) -> List[Dict[str, Any]]:
        """Récupérer les challenges actifs"""
        url = f"https://api.gurushots.com/rest/get_my_active_challenges"
        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux i686; rv:39.0) Gecko/20100101 Firefox/39.0',
            'x-api-version': '8',
            'x-env': 'WEB', 
            'X-requested-with': 'XMLHttpRequest',
            'X-token': self.bruno_token
        }
        
        async with aiohttp.ClientSession(
            headers=headers,
            connector=aiohttp.TCPConnector(ssl=False)
        ) as session:
            try:
                async with session.post(url) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result.get('challenges', [])
            except Exception as e:
                logger.error(f"Error getting challenges: {e}")
            return []
    
    def parse_challenge_end_time(self, challenge: Dict[str, Any]) -> Tuple[Optional[datetime], int]:
        """Parser le temps de fin d'un challenge et retourner (end_time, seconds_to_end)"""
        try:
            time_left = challenge.get('time_left', {})
            
            # Calculer les secondes restantes  
            seconds_remaining = (
                time_left.get('days', 0) * 24 * 3600 +
                time_left.get('hours', 0) * 3600 +
                time_left.get('minutes', 0) * 60 +
                time_left.get('seconds', 0)
            )
            
            if seconds_remaining <= 0:
                return None, 0
                
            # Calculer l'heure de fin
            end_time = datetime.now(timezone.utc) + timedelta(seconds=seconds_remaining)
            return end_time, seconds_remaining
            
        except Exception as e:
            logger.error(f"Error parsing end time: {e}")
            return None, 0
    
    async def get_challenge_followings(self, challenge_id: str) -> Dict[str, Any]:
        """Récupérer les followings d'un challenge"""
        url = f"https://api.gurushots.com/rest/get_top_photographer"
        
        payload = {
            'c_id': str(challenge_id),
            'filter': 'following',
            'init': 'true',
            'limit_above': '100',
            'limit_below': '100'
        }
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux i686; rv:39.0) Gecko/20100101 Firefox/39.0',
            'x-api-version': '8',
            'x-env': 'WEB',
            'X-requested-with': 'XMLHttpRequest',
            'X-token': self.bruno_token
        }
        
        async with aiohttp.ClientSession(
            headers=headers,
            connector=aiohttp.TCPConnector(ssl=False)
        ) as session:
            try:
                async with session.post(url, data=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result
            except Exception as e:
                logger.error(f"Error getting followings for challenge {challenge_id}: {e}")
            return {"success": False, "error": str(e)}
    
    def store_followings_data(self, snapshot_id: int, followings_data: Dict[str, Any], 
                             previous_snapshot_id: Optional[int] = None):
        """Stocker les données des followings (logique du collector enhanced)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Récupérer les données du snapshot précédent pour comparaison
        previous_data = {}
        if previous_snapshot_id:
            cursor.execute('''
                SELECT ps.member_id, ps.total_votes, ps.total_rank, ps.total_percent,
                       GROUP_CONCAT(ph.photo_id || ':' || ph.votes || ':' || ph.boost_timestamp || ':' || ph.turbo_timestamp, '|') as photos
                FROM participant_snapshots ps
                LEFT JOIN photo_snapshots ph ON ps.id = ph.participant_snapshot_id
                WHERE ps.snapshot_id = ?
                GROUP BY ps.member_id
            ''', (previous_snapshot_id,))
            
            for row in cursor.fetchall():
                member_id, votes, rank, percent, photos_str = row
                previous_data[member_id] = {
                    'votes': votes,
                    'rank': rank,
                    'percent': percent,
                    'photos': photos_str or ''
                }
        
        items = followings_data.get('items', [])
        events_detected = []
        
        for following in items:
            member = following.get('member', {})
            member_id = member.get('id')
            total_data = following.get('total', {})
            entries = following.get('entries', [])
            
            if not member_id:
                continue
            
            # Stocker/mettre à jour les données du membre
            cursor.execute('''
                INSERT OR REPLACE INTO members 
                (id, username, name, country_code, member_status, member_status_name, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (
                member_id,
                member.get('user_name', ''),
                member.get('name', ''),
                member.get('country_code', ''),
                member.get('member_status', 0),
                member.get('member_status_name', '')
            ))
            
            # Stocker les données du participant avec PERCENT
            cursor.execute('''
                INSERT INTO participant_snapshots 
                (snapshot_id, member_id, total_votes, total_rank, total_level, 
                 total_level_name, total_percent, photos_count, guru_picks_count, following_status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                snapshot_id, member_id,
                total_data.get('votes', 0),
                total_data.get('rank', 0), 
                total_data.get('level', 0),
                total_data.get('level_name', ''),
                total_data.get('percent', 0.0),
                len(entries),
                total_data.get('guru_picks', 0),
                member.get('following', True)
            ))
            
            participant_snapshot_id = cursor.lastrowid
            
            # Analyser les changements pour détecter les événements
            previous_member_data = previous_data.get(member_id, {})
            previous_photos = previous_member_data.get('photos', '').split('|') if previous_member_data else []
            previous_photos_dict = {}
            
            for photo_info in previous_photos:
                if ':' in photo_info:
                    parts = photo_info.split(':')
                    if len(parts) >= 4:
                        photo_id, votes, boost, turbo = parts[0], int(parts[1]), parts[2], parts[3]
                        previous_photos_dict[photo_id] = {
                            'votes': votes, 
                            'boost': boost,
                            'turbo': turbo
                        }
            
            # Stocker les photos
            for entry in entries:
                photo_id = entry.get('id', '')
                votes = entry.get('votes', 0)
                boost_timestamp = entry.get('boost', -1)
                turbo_timestamp = entry.get('turbo', -1)
                if turbo_timestamp == -1:
                    turbo_timestamp = entry.get('turbo_timestamp', -1)
                if turbo_timestamp == -1:
                    if entry.get('is_turbo', False) or entry.get('has_turbo', False):
                        turbo_timestamp = int(time.time())
                
                guru_pick = entry.get('guru_pick', False)
                
                cursor.execute('''
                    INSERT INTO photo_snapshots 
                    (participant_snapshot_id, photo_id, votes, rank, boost_timestamp, 
                     turbo_timestamp, guru_pick, event_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    participant_snapshot_id, photo_id, votes, entry.get('rank', 0),
                    boost_timestamp, turbo_timestamp, guru_pick, entry.get('event_id', '')
                ))
                
                # Détection d'événements
                if photo_id not in previous_photos_dict:
                    # Nouvelle photo = SUBMIT
                    events_detected.append({
                        'type': 'submit',
                        'member_id': member_id,
                        'photo_id': photo_id,
                        'metadata': {'votes': votes, 'rank': entry.get('rank', 0)}
                    })
                else:
                    previous_photo = previous_photos_dict[photo_id]
                    
                    # Détection BOOST
                    if previous_photo['boost'] == '-1' and boost_timestamp != -1:
                        events_detected.append({
                            'type': 'boost',
                            'member_id': member_id,
                            'photo_id': photo_id,
                            'metadata': {'boost_timestamp': boost_timestamp, 'votes': votes}
                        })
                    
                    # Détection TURBO
                    if previous_photo['turbo'] == '-1' and turbo_timestamp != -1:
                        events_detected.append({
                            'type': 'turbo',
                            'member_id': member_id,
                            'photo_id': photo_id,
                            'metadata': {'turbo_timestamp': turbo_timestamp, 'votes': votes}
                        })
        
        # Stocker les événements détectés  
        for event in events_detected:
            cursor.execute('''
                INSERT INTO events 
                (snapshot_id, member_id, photo_id, event_type, seconds_to_end, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                snapshot_id, event['member_id'], event.get('photo_id'),
                event['type'], 0, json.dumps(event['metadata'])  # seconds_to_end sera mis à jour après
            ))
        
        conn.commit()
        conn.close()
        
        return len(events_detected)
    
    async def collect_and_schedule_next(self, challenge_id: str, challenge_title: str):
        """Collecter les données ET programmer la prochaine collecte"""
        start_time = datetime.now(timezone.utc)
        
        logger.info(f"🎯 [ADAPTIVE COLLECT] {challenge_title}")
        
        try:
            # 1. Récupérer les données actuelles du challenge
            challenges = await self.get_my_active_challenges()
            current_challenge = None
            
            for challenge in challenges:
                if challenge['id'] == challenge_id:
                    current_challenge = challenge
                    break
            
            if not current_challenge:
                logger.warning(f"⚠️  Challenge {challenge_title} not found or ended")
                return
            
            # 2. Parser le temps restant RÉEL
            end_time, seconds_to_end = self.parse_challenge_end_time(current_challenge)
            
            if seconds_to_end <= 0:
                logger.info(f"🏁 Challenge {challenge_title} ended")
                return
            
            # 3. Trouver la stratégie active
            active_strategy = self.find_active_strategy(seconds_to_end)
            
            if not active_strategy:
                logger.warning(f"⚠️  No strategy found for {seconds_to_end}s remaining")
                return
            
            logger.info(f"📋 Using strategy: {active_strategy.name}")
            logger.info(f"⏰ Time remaining: {seconds_to_end}s ({seconds_to_end/3600:.1f}h)")
            
            # 4. Récupérer les followings
            followings_data = await self.get_challenge_followings(challenge_id)
            
            if followings_data and not followings_data.get('error'):
                # 5. Créer le snapshot
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                # Calculer la prochaine collecte
                interval_seconds = self.parse_interval_to_seconds(active_strategy.interval)
                next_collection_time = start_time + timedelta(seconds=interval_seconds) if interval_seconds else None
                
                cursor.execute('''
                    INSERT INTO snapshots 
                    (challenge_id, seconds_to_end, total_participants, collection_phase, 
                     active_strategy, next_collection_in, scheduled_time)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    challenge_id, 
                    seconds_to_end,
                    len(followings_data.get('items', [])),
                    active_strategy.name,
                    active_strategy.name,
                    interval_seconds,
                    start_time.isoformat()
                ))
                
                snapshot_id = cursor.lastrowid
                
                # Chercher le dernier snapshot pour la comparaison
                cursor.execute('''
                    SELECT id FROM snapshots 
                    WHERE challenge_id = ? AND id < ?
                    ORDER BY timestamp DESC 
                    LIMIT 1
                ''', (challenge_id, snapshot_id))
                
                result = cursor.fetchone()
                previous_snapshot_id = result[0] if result else None
                
                # Mettre à jour les events avec seconds_to_end correct
                cursor.execute('''
                    UPDATE events 
                    SET seconds_to_end = ? 
                    WHERE snapshot_id = ? AND seconds_to_end = 0
                ''', (seconds_to_end, snapshot_id))
                
                conn.commit()
                conn.close()
                
                # 6. Stocker les données des followings
                events_count = self.store_followings_data(
                    snapshot_id, followings_data, previous_snapshot_id
                )
                
                # 7. Programmer la prochaine collecte
                if next_collection_time and interval_seconds:
                    # Vérifier que le challenge n'est pas fini avant la prochaine collecte
                    if next_collection_time < end_time:
                        job_id = f"collect_{challenge_id}_next"
                        
                        # Supprimer l'ancien job s'il existe
                        try:
                            self.scheduler.remove_job(job_id)
                        except:
                            pass
                        
                        # Programmer le nouveau job
                        self.scheduler.add_job(
                            func=self.collect_and_schedule_next,
                            trigger=DateTrigger(run_date=next_collection_time),
                            args=[challenge_id, challenge_title],
                            id=job_id,
                            name=f"Next collect {challenge_title}",
                            replace_existing=True
                        )
                        
                        time_until_next = (next_collection_time - start_time).total_seconds()
                        logger.info(f"📅 Next collection in {time_until_next/60:.1f}min using {active_strategy.interval}")
                    else:
                        logger.info(f"🏁 No more collections needed for {challenge_title}")
                
                # Log du résultat
                duration = (datetime.now(timezone.utc) - start_time).total_seconds()
                followings_count = len(followings_data.get('items', []))
                
                logger.info(f"✅ [COLLECTED] {challenge_title}")
                logger.info(f"   📊 {followings_count} followings, {events_count} events")
                logger.info(f"   ⏱️  Duration: {duration:.1f}s")
                
            else:
                error_msg = followings_data.get('error', 'Unknown error')
                logger.error(f"❌ [FAILED] {challenge_title}: {error_msg}")
                
        except Exception as e:
            logger.error(f"❌ [ERROR] {challenge_title}: {e}")
    
    async def start_challenge_collection(self, challenge: Dict[str, Any]):
        """Démarrer la collecte adaptative pour un challenge"""
        challenge_id = challenge['id']
        challenge_title = challenge.get('title', 'Unknown')
        
        # Parser l'heure de fin
        end_time, seconds_to_end = self.parse_challenge_end_time(challenge)
        if not end_time or seconds_to_end <= 0:
            logger.warning(f"⚠️  Challenge {challenge_title} already ended or invalid")
            return
        
        # Trouver la stratégie de départ
        initial_strategy = self.find_active_strategy(seconds_to_end)
        if not initial_strategy:
            logger.warning(f"⚠️  No initial strategy for {challenge_title} ({seconds_to_end}s)")
            return
        
        # Sauvegarder les informations du challenge
        self.active_challenges[challenge_id] = {
            'title': challenge_title,
            'end_time': end_time,
            'initial_seconds': seconds_to_end
        }
        
        # Programmer la première collecte IMMÉDIATEMENT (dans 5 secondes)
        first_collection_time = datetime.now(timezone.utc) + timedelta(seconds=5)
        job_id = f"collect_{challenge_id}_initial"
        
        self.scheduler.add_job(
            func=self.collect_and_schedule_next,
            trigger=DateTrigger(run_date=first_collection_time),
            args=[challenge_id, challenge_title],
            id=job_id,
            name=f"Initial collect {challenge_title}",
            replace_existing=True
        )
        
        logger.info(f"✅ Started adaptive collection for {challenge_title}")
        logger.info(f"   ⏰ {seconds_to_end}s remaining ({seconds_to_end/3600:.1f}h)")
        logger.info(f"   📋 Initial strategy: {initial_strategy.name}")
        logger.info(f"   🚀 First collection in 5 seconds")
    
    async def start(self):
        """Démarrer le collector adaptatif"""
        logger.info("🎯 Starting Adaptive Collection Scheduler")
        
        self.scheduler.start()
        self._running = True
        
        # Récupérer les challenges actifs
        challenges = await self.get_my_active_challenges()
        
        if not challenges:
            logger.warning("⚠️  No active challenges found")
            return
        
        logger.info(f"📊 Found {len(challenges)} active challenges")
        
        # Démarrer la collecte adaptative pour chaque challenge
        for challenge in challenges:
            await self.start_challenge_collection(challenge)
        
        logger.info(f"✅ Adaptive Scheduler started for {len(challenges)} challenges")
        
        # Mainloop
        try:
            while self._running:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("🛑 Stopping by user request")
            self.stop()
    
    def stop(self):
        """Arrêter le collector"""
        logger.info("🛑 Stopping Adaptive Collection Scheduler")
        self._running = False
        self.scheduler.shutdown(wait=True)
        logger.info("✅ Scheduler stopped")
    
    def status(self):
        """Afficher le status du scheduler"""
        print("\n🎯 ADAPTIVE COLLECTION SCHEDULER STATUS")
        print("=" * 50)
        
        if not self._running:
            print("❌ Scheduler: STOPPED")
            return
        
        print("✅ Scheduler: RUNNING")
        
        total_jobs = len(self.scheduler.get_jobs())
        print(f"📅 Active jobs: {total_jobs}")
        
        print(f"\n📋 STRATEGIES LOADED ({len(self.strategies)}):")
        for strategy in self.strategies:
            print(f"   • {strategy.name}: {strategy.description}")
            print(f"     {strategy.from_time} → {strategy.to_time} (every {strategy.interval})")
        
        if self.active_challenges:
            print(f"\n🎯 ACTIVE CHALLENGES ({len(self.active_challenges)}):")
            
            now = datetime.now(timezone.utc)
            for challenge_id, info in self.active_challenges.items():
                challenge_title = info['title']
                end_time = info['end_time']
                
                time_remaining = (end_time - now).total_seconds()
                
                if time_remaining > 0:
                    active_strategy = self.find_active_strategy(int(time_remaining))
                    strategy_name = active_strategy.name if active_strategy else "No strategy"
                    
                    print(f"   📊 {challenge_title}:")
                    print(f"      Time remaining: {time_remaining/3600:.1f}h")
                    print(f"      Current strategy: {strategy_name}")
                else:
                    print(f"   🏁 {challenge_title}: ENDED")


def load_bruno_token() -> Optional[str]:
    """Charger le token bruno depuis gsgui.ini"""
    config_path = "data/gsgui.ini"
    
    if not os.path.exists(config_path):
        return None
    
    try:
        with open(config_path, 'r') as f:
            lines = f.readlines()
        
        in_bruno_section = False
        for line in lines:
            line = line.strip()
            if line == "[[bruno]]":
                in_bruno_section = True
                continue
            if line.startswith("[[") and line != "[[bruno]]":
                in_bruno_section = False
                continue
            if in_bruno_section and line.startswith("xtoken = "):
                return line.split("xtoken = ")[1].strip()
    except Exception as e:
        logger.error(f"Error reading token: {e}")
    
    return None


async def main():
    """Fonction principale"""

    # Utiliser la base de données locale
    database_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'gurushots_adaptive.db')
    logger.info(f"✅ Using database: {database_path}")
    
    # Charger token
    token = load_bruno_token()
    if not token:
        logger.error("❌ Bruno token not found in gsgui.ini")
        return
    
    # Configuration
    config = CollectionConfig(
        database_path=database_path,
        bruno_token=token,
        strategies_file="collection_strategies.ini"
    )
    
    # Démarrer le scheduler adaptatif
    scheduler = AdaptiveCollectionScheduler(config)
    await scheduler.start()


if __name__ == "__main__":
    asyncio.run(main())