"""
GuruShots Analytics Database Schema
Optimized for pattern analysis and strategy detection
Storage: /Volumes/SSD/Data/gurushots_analytics.db
"""

import sqlite3
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
import json

logger = logging.getLogger(__name__)

class GuruShotsAnalyticsDB:
    """
    Advanced analytics database for GuruShots challenge patterns
    Stores TOP 1000 participants every 30 minutes for pattern analysis
    """
    
    def __init__(self, db_path: str = "/Volumes/SSD/Data/gurushots_analytics.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create database connection
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row  # Enable dict-like access
        
        # Create tables
        self._create_tables()
        
        logger.info(f"📊 Analytics DB initialized: {self.db_path}")
    
    def _create_tables(self):
        """Create optimized tables for analytics"""
        
        # Challenges table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS challenges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                challenge_id TEXT UNIQUE NOT NULL,
                challenge_url TEXT NOT NULL,
                title TEXT NOT NULL,
                start_time DATETIME,
                end_time DATETIME NOT NULL,
                status TEXT DEFAULT 'active',  -- active, ended, archived
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                
                INDEX idx_challenge_id (challenge_id),
                INDEX idx_end_time (end_time),
                INDEX idx_status (status)
            )
        """)
        
        # Snapshots table - Each collection cycle
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                challenge_id TEXT NOT NULL,
                timestamp DATETIME NOT NULL,
                time_left_hours INTEGER,  -- Hours remaining
                time_left_minutes INTEGER, -- Minutes remaining  
                total_participants INTEGER,
                total_votes_in_challenge INTEGER,
                snapshot_type TEXT DEFAULT 'regular',  -- regular, final, hourly
                
                FOREIGN KEY (challenge_id) REFERENCES challenges (challenge_id),
                INDEX idx_challenge_timestamp (challenge_id, timestamp),
                INDEX idx_time_left (time_left_hours, time_left_minutes),
                INDEX idx_snapshot_type (snapshot_type)
            )
        """)
        
        # Participants table - TOP 1000 each snapshot
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS participants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_id INTEGER NOT NULL,
                rank INTEGER NOT NULL,
                user_id TEXT NOT NULL,
                username TEXT NOT NULL,
                display_name TEXT,
                total_votes INTEGER NOT NULL,
                photo_count INTEGER DEFAULT 0,
                is_boosted BOOLEAN DEFAULT FALSE,
                is_guru_pick BOOLEAN DEFAULT FALSE,
                
                -- Analytics fields
                votes_delta INTEGER DEFAULT 0,  -- Change since last snapshot
                rank_delta INTEGER DEFAULT 0,   -- Rank change since last
                first_seen_at DATETIME,         -- When first detected in challenge
                
                FOREIGN KEY (snapshot_id) REFERENCES snapshots (id),
                INDEX idx_snapshot_rank (snapshot_id, rank),
                INDEX idx_user_challenge (user_id, snapshot_id),
                INDEX idx_username (username),
                INDEX idx_rank_range (rank),
                INDEX idx_votes_range (total_votes)
            )
        """)
        
        # Photos table - Each photo per participant
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS photos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                participant_id INTEGER NOT NULL,
                photo_id TEXT NOT NULL,
                votes INTEGER NOT NULL,
                is_boosted BOOLEAN DEFAULT FALSE,
                is_guru_pick BOOLEAN DEFAULT FALSE,
                boost_timestamp DATETIME,
                
                -- Analytics fields
                votes_delta INTEGER DEFAULT 0,  -- Change since last snapshot
                first_seen_at DATETIME,         -- When photo first appeared
                last_seen_at DATETIME,          -- When photo last seen (for swap detection)
                
                FOREIGN KEY (participant_id) REFERENCES participants (id),
                INDEX idx_participant_photo (participant_id, photo_id),
                INDEX idx_photo_votes (votes DESC),
                INDEX idx_boost_status (is_boosted),
                INDEX idx_guru_pick (is_guru_pick)
            )
        """)
        
        # Events table - Detected strategic events
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                challenge_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                username TEXT NOT NULL,
                event_type TEXT NOT NULL,  -- entry, swap_out, swap_in, fill, boost, rank_jump
                timestamp DATETIME NOT NULL,
                time_left_hours INTEGER,
                time_left_minutes INTEGER,
                
                -- Event data
                rank_before INTEGER,
                rank_after INTEGER,
                votes_before INTEGER,
                votes_after INTEGER,
                photo_id TEXT,  -- For photo-specific events
                additional_data TEXT,  -- JSON for extra event data
                
                -- Pattern detection
                pattern_score REAL DEFAULT 0.0,  -- How significant is this event
                is_top_performer BOOLEAN DEFAULT FALSE,  -- Is this a top 10 performer
                
                FOREIGN KEY (challenge_id) REFERENCES challenges (challenge_id),
                INDEX idx_event_type (event_type),
                INDEX idx_challenge_time (challenge_id, timestamp),
                INDEX idx_user_events (user_id, event_type),
                INDEX idx_top_performers (is_top_performer, event_type),
                INDEX idx_timing (time_left_hours, time_left_minutes)
            )
        """)
        
        # Winners analysis table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS winners_analysis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                challenge_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                username TEXT NOT NULL,
                final_rank INTEGER NOT NULL,
                final_votes INTEGER NOT NULL,
                
                -- Timing analysis
                entry_time_hours_before_end INTEGER,  -- When they entered
                first_fill_hours_before_end INTEGER,  -- First major vote increase
                last_activity_hours_before_end INTEGER,  -- Last significant action
                
                -- Strategy patterns
                total_swaps INTEGER DEFAULT 0,
                total_fills INTEGER DEFAULT 0,  -- Major vote increases
                used_boost BOOLEAN DEFAULT FALSE,
                boost_timing_hours_before_end INTEGER,
                
                -- Success metrics
                win_probability REAL DEFAULT 0.0,  -- Based on pattern analysis
                strategy_pattern TEXT,  -- Detected strategy type
                
                FOREIGN KEY (challenge_id) REFERENCES challenges (challenge_id),
                INDEX idx_challenge_winner (challenge_id, final_rank),
                INDEX idx_strategy_pattern (strategy_pattern),
                INDEX idx_entry_timing (entry_time_hours_before_end)
            )
        """)
        
        self.conn.commit()
        logger.info("✅ Analytics database tables created/verified")
    
    def store_challenge_snapshot(self, challenge_data: Dict, participants_data: List[Dict]) -> int:
        """Store a complete challenge snapshot"""
        
        challenge_id = challenge_data['challenge_id']
        timestamp = datetime.now()
        
        # Store/update challenge info
        self.conn.execute("""
            INSERT OR REPLACE INTO challenges 
            (challenge_id, challenge_url, title, end_time, status)
            VALUES (?, ?, ?, ?, ?)
        """, (
            challenge_id,
            challenge_data['challenge_url'],
            challenge_data['title'],
            challenge_data['end_time'],
            challenge_data.get('status', 'active')
        ))
        
        # Store snapshot
        cursor = self.conn.execute("""
            INSERT INTO snapshots 
            (challenge_id, timestamp, time_left_hours, time_left_minutes, 
             total_participants, total_votes_in_challenge)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            challenge_id,
            timestamp,
            challenge_data.get('time_left_hours', 0),
            challenge_data.get('time_left_minutes', 0),
            len(participants_data),
            challenge_data.get('total_votes', 0)
        ))
        
        snapshot_id = cursor.lastrowid
        
        # Store participants and their photos
        for participant in participants_data:
            self._store_participant(snapshot_id, participant)
        
        self.conn.commit()
        logger.info(f"📊 Stored snapshot for challenge {challenge_id}: {len(participants_data)} participants")
        
        return snapshot_id
    
    def _store_participant(self, snapshot_id: int, participant_data: Dict):
        """Store participant and their photos"""
        
        # Store participant
        cursor = self.conn.execute("""
            INSERT INTO participants
            (snapshot_id, rank, user_id, username, display_name, total_votes, photo_count)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            snapshot_id,
            participant_data['rank'],
            participant_data['user_id'],
            participant_data['username'],
            participant_data.get('display_name', ''),
            participant_data['total_votes'],
            len(participant_data.get('photos', []))
        ))
        
        participant_id = cursor.lastrowid
        
        # Store participant's photos
        for photo in participant_data.get('photos', []):
            self.conn.execute("""
                INSERT INTO photos
                (participant_id, photo_id, votes, is_boosted, is_guru_pick)
                VALUES (?, ?, ?, ?, ?)
            """, (
                participant_id,
                photo['photo_id'],
                photo['votes'],
                photo.get('is_boosted', False),
                photo.get('is_guru_pick', False)
            ))
    
    def detect_events_since_last_snapshot(self, challenge_id: str) -> List[Dict]:
        """Detect strategic events by comparing with previous snapshot"""
        
        # Get last two snapshots
        snapshots = self.conn.execute("""
            SELECT id, timestamp FROM snapshots 
            WHERE challenge_id = ? 
            ORDER BY timestamp DESC LIMIT 2
        """, (challenge_id,)).fetchall()
        
        if len(snapshots) < 2:
            return []  # Need at least 2 snapshots to compare
        
        current_snapshot_id, previous_snapshot_id = snapshots[0]['id'], snapshots[1]['id']
        
        events = []
        
        # Detect new entries (users who weren't in previous snapshot)
        new_entries = self.conn.execute("""
            SELECT p.user_id, p.username, p.rank, p.total_votes,
                   s.time_left_hours, s.time_left_minutes
            FROM participants p
            JOIN snapshots s ON p.snapshot_id = s.id
            WHERE p.snapshot_id = ? 
            AND p.user_id NOT IN (
                SELECT user_id FROM participants WHERE snapshot_id = ?
            )
            AND p.rank <= 100  -- Focus on top performers
        """, (current_snapshot_id, previous_snapshot_id)).fetchall()
        
        for entry in new_entries:
            events.append({
                'event_type': 'entry',
                'user_id': entry['user_id'],
                'username': entry['username'],
                'rank_after': entry['rank'],
                'votes_after': entry['total_votes'],
                'time_left_hours': entry['time_left_hours'],
                'time_left_minutes': entry['time_left_minutes'],
                'is_top_performer': entry['rank'] <= 10
            })
        
        # Detect significant vote increases (fills)
        fills = self.conn.execute("""
            SELECT 
                p1.user_id, p1.username, p1.rank as current_rank, p1.total_votes as current_votes,
                p2.total_votes as previous_votes, p2.rank as previous_rank,
                s.time_left_hours, s.time_left_minutes,
                (p1.total_votes - p2.total_votes) as votes_increase
            FROM participants p1
            JOIN participants p2 ON p1.user_id = p2.user_id
            JOIN snapshots s ON p1.snapshot_id = s.id
            WHERE p1.snapshot_id = ? AND p2.snapshot_id = ?
            AND (p1.total_votes - p2.total_votes) >= 50  -- Significant vote increase
            AND p1.rank <= 100
        """, (current_snapshot_id, previous_snapshot_id)).fetchall()
        
        for fill in fills:
            events.append({
                'event_type': 'fill',
                'user_id': fill['user_id'],
                'username': fill['username'],
                'rank_before': fill['previous_rank'],
                'rank_after': fill['current_rank'],
                'votes_before': fill['previous_votes'],
                'votes_after': fill['current_votes'],
                'time_left_hours': fill['time_left_hours'],
                'time_left_minutes': fill['time_left_minutes'],
                'votes_increase': fill['votes_increase'],
                'is_top_performer': fill['current_rank'] <= 10
            })
        
        # Store detected events
        for event in events:
            self._store_event(challenge_id, event)
        
        return events
    
    def _store_event(self, challenge_id: str, event_data: Dict):
        """Store a detected strategic event"""
        
        self.conn.execute("""
            INSERT INTO events
            (challenge_id, user_id, username, event_type, timestamp,
             time_left_hours, time_left_minutes, rank_before, rank_after,
             votes_before, votes_after, photo_id, additional_data, is_top_performer)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            challenge_id,
            event_data['user_id'],
            event_data['username'],
            event_data['event_type'],
            datetime.now(),
            event_data.get('time_left_hours'),
            event_data.get('time_left_minutes'),
            event_data.get('rank_before'),
            event_data.get('rank_after'),
            event_data.get('votes_before'),
            event_data.get('votes_after'),
            event_data.get('photo_id'),
            json.dumps(event_data.get('additional_data', {})),
            event_data.get('is_top_performer', False)
        ))
    
    def analyze_top_winners_entry_timing(self, limit: int = 50) -> List[Dict]:
        """Analyze when top 10 winners typically enter challenges"""
        
        results = self.conn.execute("""
            SELECT 
                username,
                AVG(entry_time_hours_before_end) as avg_entry_timing,
                COUNT(*) as wins_count,
                strategy_pattern,
                AVG(final_votes) as avg_final_votes
            FROM winners_analysis 
            WHERE final_rank <= 10
            GROUP BY username, strategy_pattern
            HAVING wins_count >= 2  -- At least 2 wins for pattern
            ORDER BY wins_count DESC, avg_final_votes DESC
            LIMIT ?
        """, (limit,)).fetchall()
        
        return [dict(row) for row in results]
    
    def analyze_fill_patterns(self, top_n: int = 10) -> List[Dict]:
        """Analyze when top performers do their major fills"""
        
        results = self.conn.execute("""
            SELECT 
                time_left_hours,
                time_left_minutes,
                COUNT(*) as fill_count,
                AVG(votes_after - votes_before) as avg_votes_increase,
                COUNT(DISTINCT user_id) as unique_users
            FROM events 
            WHERE event_type = 'fill' 
            AND is_top_performer = TRUE
            AND (votes_after - votes_before) >= 100  -- Significant fills only
            GROUP BY time_left_hours, time_left_minutes
            ORDER BY fill_count DESC
            LIMIT ?
        """, (top_n,)).fetchall()
        
        return [dict(row) for row in results]
    
    def get_user_strategy_pattern(self, username: str, days_back: int = 30) -> Dict:
        """Analyze a specific user's strategy patterns"""
        
        # Get recent events for this user
        events = self.conn.execute("""
            SELECT event_type, time_left_hours, time_left_minutes, 
                   rank_before, rank_after, votes_before, votes_after
            FROM events 
            WHERE username = ? 
            AND timestamp >= datetime('now', '-{} days')
            ORDER BY timestamp DESC
        """.format(days_back), (username,)).fetchall()
        
        # Analyze patterns
        pattern = {
            'username': username,
            'total_events': len(events),
            'entry_timings': [],
            'fill_timings': [],
            'avg_entry_hours_before': 0,
            'avg_fill_hours_before': 0,
            'strategy_score': 0
        }
        
        for event in events:
            if event['event_type'] == 'entry':
                pattern['entry_timings'].append(event['time_left_hours'])
            elif event['event_type'] == 'fill':
                pattern['fill_timings'].append(event['time_left_hours'])
        
        if pattern['entry_timings']:
            pattern['avg_entry_hours_before'] = sum(pattern['entry_timings']) / len(pattern['entry_timings'])
        
        if pattern['fill_timings']:
            pattern['avg_fill_hours_before'] = sum(pattern['fill_timings']) / len(pattern['fill_timings'])
        
        return pattern
    
    def get_database_stats(self) -> Dict:
        """Get database statistics"""
        
        stats = {}
        
        # Basic counts
        stats['total_challenges'] = self.conn.execute("SELECT COUNT(*) FROM challenges").fetchone()[0]
        stats['total_snapshots'] = self.conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0]
        stats['total_participants'] = self.conn.execute("SELECT COUNT(*) FROM participants").fetchone()[0]
        stats['total_photos'] = self.conn.execute("SELECT COUNT(*) FROM photos").fetchone()[0]
        stats['total_events'] = self.conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        
        # Recent activity
        stats['challenges_last_24h'] = self.conn.execute("""
            SELECT COUNT(*) FROM snapshots 
            WHERE timestamp >= datetime('now', '-1 day')
        """).fetchone()[0]
        
        stats['events_last_24h'] = self.conn.execute("""
            SELECT COUNT(*) FROM events 
            WHERE timestamp >= datetime('now', '-1 day')
        """).fetchone()[0]
        
        # Top event types
        event_types = self.conn.execute("""
            SELECT event_type, COUNT(*) as count
            FROM events 
            GROUP BY event_type 
            ORDER BY count DESC
        """).fetchall()
        
        stats['event_types'] = {row['event_type']: row['count'] for row in event_types}
        
        return stats

# Global instance
analytics_db = None

def get_analytics_db() -> GuruShotsAnalyticsDB:
    """Get or create analytics database instance"""
    global analytics_db
    if analytics_db is None:
        analytics_db = GuruShotsAnalyticsDB()
    return analytics_db
