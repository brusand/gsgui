"""
ANCA Intelligence Service
Dedicated surveillance program for monitoring ANCA the vampire (anca.chilom)
Analyzes patterns, stores data, and provides strategic insights
"""

import asyncio
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import aiohttp
from configobj import ConfigObj

from app.services.gurushots_api import GuruShotsAPI
from app.websockets.connection_manager import connection_manager

logger = logging.getLogger(__name__)

@dataclass
class AncaEvent:
    """Structure for ANCA events"""
    timestamp: str
    challenge_id: int
    challenge_url: str
    event_type: str  # 'entry', 'swap', 'boost', 'vote_change', 'rank_change'
    photo_id: Optional[str] = None
    previous_photo_id: Optional[str] = None
    votes: Optional[int] = None
    rank: Optional[int] = None
    time_left: Optional[str] = None
    additional_data: Optional[Dict[str, Any]] = None

@dataclass
class AncaPattern:
    """Detected pattern in ANCA's behavior"""
    pattern_type: str
    frequency: int
    success_rate: float
    timing_windows: List[str]
    conditions: Dict[str, Any]
    confidence_score: float

class AncaIntelligenceService:
    """
    Advanced surveillance and analysis service for ANCA the vampire
    """
    
    def __init__(self, gurushots_api: GuruShotsAPI, user_id: str = "anca_watcher"):
        self.api = gurushots_api
        self.user_id = user_id
        self.anca_username = "anca.chilom"
        self.anca_user_id = None
        
        # Data storage
        self.anca_events: List[AncaEvent] = []
        self.challenge_data: Dict[int, Dict] = {}  # challenge_id -> data
        self.detected_patterns: List[AncaPattern] = []
        
        # Surveillance state
        self.active_challenges: Dict[int, bool] = {}  # challenge_id -> active
        self.last_known_state: Dict[int, Dict] = {}   # challenge_id -> last state
        
        # Analysis parameters
        self.min_pattern_occurrences = 3
        self.pattern_confidence_threshold = 0.7
        
        # Configuration
        self.surveillance_config = ConfigObj('anca_surveillance.ini')
        self._init_config()
        
    def _init_config(self):
        """Initialize surveillance configuration"""
        if not self.surveillance_config.get('anca'):
            self.surveillance_config['anca'] = {
                'username': self.anca_username,
                'monitoring_enabled': True,
                'alert_thresholds': {
                    'rapid_swaps': 3,  # 3 swaps in short time = alert
                    'early_entry': '24h',  # Entry more than 24h before = notable
                    'boost_timing': '12h'   # Boost timing windows
                }
            }
            self.surveillance_config.write()
    
    async def start_surveillance(self, challenge_ids: List[int] = None):
        """Start monitoring ANCA across challenges"""
        logger.info(f"🔍 Starting ANCA surveillance for {self.anca_username}")
        
        try:
            # Get ANCA's user ID if not cached
            if not self.anca_user_id:
                self.anca_user_id = await self._get_anca_user_id()
                if not self.anca_user_id:
                    logger.error("Could not find ANCA's user ID")
                    return False
            
            # If no specific challenges, monitor all active ones
            if not challenge_ids:
                challenges = await self.api.get_challenges()
                challenge_ids = [int(ch['id']) for ch in challenges.get('challenges', [])]
            
            # Start monitoring each challenge
            for challenge_id in challenge_ids:
                if challenge_id not in self.active_challenges:
                    self.active_challenges[challenge_id] = True
                    asyncio.create_task(self._monitor_challenge(challenge_id))
            
            # Start pattern analysis task
            asyncio.create_task(self._pattern_analysis_loop())
            
            await connection_manager.send_personal_message(self.user_id, {
                "type": "anca_surveillance_started",
                "message": f"Started monitoring ANCA in {len(challenge_ids)} challenges",
                "challenges": challenge_ids
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Error starting ANCA surveillance: {str(e)}")
            return False
    
    async def _get_anca_user_id(self) -> Optional[int]:
        """Get ANCA's user ID from her profile"""
        try:
            # Use the profile URL to get user ID
            profile_url = f"https://gurushots.com/{self.anca_username}/photos"
            # This would need to be implemented in GuruShotsAPI
            # For now, we'll search in followings of active challenges
            logger.info("Searching for ANCA's user ID...")
            return None  # Placeholder - would be implemented with API call
            
        except Exception as e:
            logger.error(f"Error getting ANCA user ID: {str(e)}")
            return None
    
    async def _monitor_challenge(self, challenge_id: int):
        """Monitor ANCA's activity in a specific challenge"""
        logger.info(f"👁️  Monitoring ANCA in challenge {challenge_id}")
        
        while self.active_challenges.get(challenge_id, False):
            try:
                # Get challenge details
                challenge_url = f"challenge-{challenge_id}"  # Placeholder URL format
                challenge_details = await self.api.get_challenge_details(challenge_url)
                
                # Check if challenge is still active
                if challenge_details.get('challenge', {}).get('close_time', 0) == 0:
                    logger.info(f"Challenge {challenge_id} ended, stopping monitoring")
                    self.active_challenges[challenge_id] = False
                    break
                
                # Get followings to find ANCA
                followings = await self.api.get_challenge_followings(challenge_id)
                anca_data = await self._find_anca_in_followings(followings, challenge_id)
                
                if anca_data:
                    await self._analyze_anca_state(challenge_id, anca_data, challenge_details)
                
                # Adaptive polling based on time left
                time_left = challenge_details.get('challenge', {}).get('time_left', {})
                sleep_time = self._calculate_poll_interval(time_left)
                await asyncio.sleep(sleep_time)
                
            except Exception as e:
                logger.error(f"Error monitoring challenge {challenge_id}: {str(e)}")
                await asyncio.sleep(60)  # Wait before retrying
        
        logger.info(f"Stopped monitoring challenge {challenge_id}")
    
    async def _find_anca_in_followings(self, followings: Dict, challenge_id: int) -> Optional[Dict]:
        """Find ANCA in the followings list"""
        items = followings.get('items', [])
        for following in items:
            if following['member']['user_name'].lower() == self.anca_username.lower():
                return following
        return None
    
    async def _analyze_anca_state(self, challenge_id: int, current_data: Dict, challenge_details: Dict):
        """Analyze ANCA's current state and detect events"""
        current_time = datetime.now().isoformat()
        time_left = challenge_details.get('challenge', {}).get('time_left', {})
        time_left_str = f"{time_left.get('days', 0)}d {time_left.get('hours', 0)}h {time_left.get('minutes', 0)}m"
        
        # Get previous state for comparison
        previous_state = self.last_known_state.get(challenge_id, {})
        
        # Detect events
        events = await self._detect_anca_events(challenge_id, current_data, previous_state, time_left_str)
        
        # Store events
        for event in events:
            self.anca_events.append(event)
            await self._notify_anca_event(event)
        
        # Update state
        self.last_known_state[challenge_id] = current_data
        
        # Store challenge data
        if challenge_id not in self.challenge_data:
            self.challenge_data[challenge_id] = {
                'url': challenge_details.get('challenge', {}).get('url', ''),
                'title': challenge_details.get('challenge', {}).get('title', ''),
                'entries_history': [],
                'events': []
            }
        
        # Add to history
        history_entry = {
            'timestamp': current_time,
            'time_left': time_left_str,
            'rank': current_data.get('total', {}).get('rank', 0),
            'votes': current_data.get('total', {}).get('votes', 0),
            'entries': [{'id': entry['id'], 'votes': entry['votes']} for entry in current_data.get('entries', [])]
        }
        
        self.challenge_data[challenge_id]['entries_history'].append(history_entry)
        self.challenge_data[challenge_id]['events'].extend([asdict(event) for event in events])
    
    async def _detect_anca_events(self, challenge_id: int, current: Dict, previous: Dict, time_left: str) -> List[AncaEvent]:
        """Detect specific events in ANCA's behavior"""
        events = []
        current_time = datetime.now().isoformat()
        
        current_entries = {entry['id']: entry for entry in current.get('entries', [])}
        previous_entries = {entry['id']: entry for entry in previous.get('entries', [])}
        
        # Detect new entries (posts)
        for entry_id, entry in current_entries.items():
            if entry_id not in previous_entries:
                event = AncaEvent(
                    timestamp=current_time,
                    challenge_id=challenge_id,
                    challenge_url=f"challenge-{challenge_id}",
                    event_type='entry',
                    photo_id=entry_id,
                    votes=entry.get('votes', 0),
                    rank=current.get('total', {}).get('rank', 0),
                    time_left=time_left,
                    additional_data={'entry_data': entry}
                )
                events.append(event)
                logger.info(f"🔥 ANCA posted new photo {entry_id} at {time_left} left")
        
        # Detect swaps (disappeared entries)
        for entry_id in previous_entries:
            if entry_id not in current_entries:
                event = AncaEvent(
                    timestamp=current_time,
                    challenge_id=challenge_id,
                    challenge_url=f"challenge-{challenge_id}",
                    event_type='swap',
                    photo_id=entry_id,
                    previous_photo_id=entry_id,
                    time_left=time_left,
                    additional_data={'swapped_out': previous_entries[entry_id]}
                )
                events.append(event)
                logger.info(f"🔄 ANCA swapped out photo {entry_id} at {time_left} left")
        
        # Detect boosts
        for entry_id, entry in current_entries.items():
            if entry_id in previous_entries:
                prev_boost = previous_entries[entry_id].get('boost', False)
                curr_boost = entry.get('boost', False)
                
                if not prev_boost and curr_boost:
                    event = AncaEvent(
                        timestamp=current_time,
                        challenge_id=challenge_id,
                        challenge_url=f"challenge-{challenge_id}",
                        event_type='boost',
                        photo_id=entry_id,
                        votes=entry.get('votes', 0),
                        time_left=time_left
                    )
                    events.append(event)
                    logger.info(f"⚡ ANCA boosted photo {entry_id} at {time_left} left")
        
        # Detect significant rank changes
        current_rank = current.get('total', {}).get('rank', 0)
        previous_rank = previous.get('total', {}).get('rank', 0)
        
        if previous_rank > 0 and current_rank > 0 and abs(current_rank - previous_rank) >= 10:
            event = AncaEvent(
                timestamp=current_time,
                challenge_id=challenge_id,
                challenge_url=f"challenge-{challenge_id}",
                event_type='rank_change',
                rank=current_rank,
                time_left=time_left,
                additional_data={
                    'previous_rank': previous_rank,
                    'rank_delta': current_rank - previous_rank
                }
            )
            events.append(event)
            logger.info(f"📈 ANCA rank changed from {previous_rank} to {current_rank} at {time_left} left")
        
        return events
    
    async def _notify_anca_event(self, event: AncaEvent):
        """Send WebSocket notification for ANCA event"""
        await connection_manager.notify_anca_activity(
            self.user_id,
            event.challenge_id,
            self.anca_username,
            event.event_type,
            asdict(event)
        )
    
    def _calculate_poll_interval(self, time_left: Dict) -> int:
        """Calculate polling interval based on time left"""
        if time_left.get('days', 0) == 0 and time_left.get('hours', 0) == 0:
            return 30  # Last hour - poll every 30 seconds
        elif time_left.get('days', 0) == 0:
            return 120  # Last day - poll every 2 minutes
        else:
            return 300  # Earlier - poll every 5 minutes
    
    async def _pattern_analysis_loop(self):
        """Continuous pattern analysis"""
        while True:
            try:
                await asyncio.sleep(1800)  # Analyze patterns every 30 minutes
                await self._analyze_patterns()
            except Exception as e:
                logger.error(f"Error in pattern analysis: {str(e)}")
    
    async def _analyze_patterns(self):
        """Analyze ANCA's behavioral patterns"""
        if len(self.anca_events) < self.min_pattern_occurrences:
            return
        
        logger.info("🧠 Analyzing ANCA behavioral patterns...")
        
        # Pattern analysis would go here
        # For now, just log the analysis
        entry_times = [event for event in self.anca_events if event.event_type == 'entry']
        swap_times = [event for event in self.anca_events if event.event_type == 'swap']
        boost_times = [event for event in self.anca_events if event.event_type == 'boost']
        
        logger.info(f"📊 ANCA stats: {len(entry_times)} entries, {len(swap_times)} swaps, {len(boost_times)} boosts")
        
        # Send pattern report
        await connection_manager.send_personal_message(self.user_id, {
            "type": "anca_pattern_analysis",
            "stats": {
                "total_events": len(self.anca_events),
                "entries": len(entry_times),
                "swaps": len(swap_times),
                "boosts": len(boost_times)
            }
        })
    
    def export_anca_data(self, filepath: str = "anca_intelligence.json"):
        """Export all collected ANCA data"""
        data = {
            'anca_username': self.anca_username,
            'export_timestamp': datetime.now().isoformat(),
            'events': [asdict(event) for event in self.anca_events],
            'challenge_data': self.challenge_data,
            'detected_patterns': [asdict(pattern) for pattern in self.detected_patterns]
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"📁 Exported ANCA data to {filepath}")
        return filepath
    
    def stop_surveillance(self):
        """Stop all surveillance activities"""
        for challenge_id in list(self.active_challenges.keys()):
            self.active_challenges[challenge_id] = False
        
        logger.info("🛑 ANCA surveillance stopped")

# Global instance
anca_intelligence = None

def get_anca_intelligence(gurushots_api: GuruShotsAPI, user_id: str = "anca_watcher") -> AncaIntelligenceService:
    """Get or create ANCA intelligence service"""
    global anca_intelligence
    if anca_intelligence is None:
        anca_intelligence = AncaIntelligenceService(gurushots_api, user_id)
    return anca_intelligence
