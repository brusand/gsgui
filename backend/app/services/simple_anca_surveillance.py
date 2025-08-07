"""
ANCA Surveillance Simple - Using existing methods + Cron MCP
Monitors ANCA the vampire using get_top_photographer() and stores events
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional
import json
from pathlib import Path

from app.services.gurushots_api import GuruShotsAPI
from app.services.config_manager import config_manager
from app.websockets.connection_manager import connection_manager

logger = logging.getLogger(__name__)

class SimpleAncaSurveillance:
    """Simple ANCA surveillance using existing methods"""
    
    def __init__(self):
        self.anca_username = "anca.chilom"
        self.storage_file = Path("anca_surveillance_data.json")
        self.last_states = {}  # challenge_id -> last_known_state
        self.events = []
        
        # Load existing data
        self._load_data()
    
    def _load_data(self):
        """Load existing surveillance data"""
        if self.storage_file.exists():
            try:
                with open(self.storage_file, 'r') as f:
                    data = json.load(f)
                    self.events = data.get('events', [])
                    self.last_states = data.get('last_states', {})
                logger.info(f"Loaded {len(self.events)} ANCA events from storage")
            except Exception as e:
                logger.error(f"Error loading ANCA data: {e}")
    
    def _save_data(self):
        """Save surveillance data"""
        try:
            data = {
                'anca_username': self.anca_username,
                'last_updated': datetime.now().isoformat(),
                'events': self.events[-1000:],  # Keep last 1000 events
                'last_states': self.last_states
            }
            with open(self.storage_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving ANCA data: {e}")
    
    async def monitor_active_challenges(self, user_token: str) -> Dict:
        """
        Monitor ANCA in all active challenges
        Called by cron job every 5-15 minutes
        """
        logger.info("🔍 Starting ANCA surveillance check...")
        
        api_client = GuruShotsAPI(user_token)
        results = {
            'challenges_checked': 0,
            'anca_found_in': 0,
            'events_detected': 0,
            'errors': []
        }
        
        try:
            # Get active challenges
            challenges_response = await api_client.get_challenges()
            challenges = challenges_response.get('challenges', [])
            
            for challenge in challenges[:5]:  # Limit to 5 challenges to avoid rate limits
                challenge_id = challenge['id']
                challenge_url = challenge['url']
                
                try:
                    # Get challenge ranking using get_top_photographer
                    ranking = await self._get_challenge_ranking(api_client, int(challenge_id))
                    results['challenges_checked'] += 1
                    
                    # Find ANCA in ranking
                    anca_data = self._find_anca_in_ranking(ranking)
                    
                    if anca_data:
                        results['anca_found_in'] += 1
                        
                        # Detect events by comparing with last state
                        events = await self._detect_anca_events(
                            challenge_id, challenge_url, anca_data
                        )
                        
                        if events:
                            results['events_detected'] += len(events)
                            self.events.extend(events)
                            
                            # Notify events
                            for event in events:
                                await self._notify_anca_event(event)
                        
                        # Update last known state
                        self.last_states[challenge_id] = anca_data
                
                except Exception as e:
                    error_msg = f"Error monitoring challenge {challenge_id}: {str(e)}"
                    logger.error(error_msg)
                    results['errors'].append(error_msg)
            
            # Save data
            self._save_data()
            
            logger.info(f"🎯 ANCA surveillance completed: {results}")
            return results
            
        except Exception as e:
            logger.error(f"Error in ANCA surveillance: {str(e)}")
            results['errors'].append(str(e))
            return results
    
    async def _get_challenge_ranking(self, api_client: GuruShotsAPI, challenge_id: int) -> Dict:
        """Get challenge ranking using existing get_top_photographer method"""
        try:
            # Use get_top_photographer without filter to get full ranking
            ranking = await api_client.get_challenge_followings(challenge_id, limit=200)
            return ranking
        except Exception as e:
            logger.error(f"Error getting challenge ranking: {e}")
            return {}
    
    def _find_anca_in_ranking(self, ranking: Dict) -> Optional[Dict]:
        """Find ANCA in the ranking data"""
        items = ranking.get('items', [])
        
        for item in items:
            member = item.get('member', {})
            if member.get('user_name', '').lower() == self.anca_username.lower():
                return {
                    'user_name': member.get('user_name'),
                    'user_id': member.get('id'),
                    'name': member.get('name', ''),
                    'rank': item.get('total', {}).get('rank', 0),
                    'votes': item.get('total', {}).get('votes', 0),
                    'entries': item.get('entries', []),
                    'timestamp': datetime.now().isoformat()
                }
        
        return None
    
    async def _detect_anca_events(self, challenge_id: str, challenge_url: str, 
                                current_data: Dict) -> List[Dict]:
        """Detect ANCA events by comparing with previous state"""
        events = []
        previous_data = self.last_states.get(challenge_id, {})
        
        if not previous_data:
            # First time seeing ANCA in this challenge
            if current_data['entries']:
                events.append({
                    'type': 'first_detection',
                    'challenge_id': challenge_id,
                    'challenge_url': challenge_url,
                    'timestamp': datetime.now().isoformat(),
                    'data': {
                        'rank': current_data['rank'],
                        'votes': current_data['votes'],
                        'entries_count': len(current_data['entries'])
                    }
                })
            return events
        
        # Compare entries for swaps/new posts
        current_entries = {entry['id']: entry for entry in current_data.get('entries', [])}
        previous_entries = {entry['id']: entry for entry in previous_data.get('entries', [])}
        
        # Detect new entries (posts)
        for entry_id, entry in current_entries.items():
            if entry_id not in previous_entries:
                events.append({
                    'type': 'new_entry',
                    'challenge_id': challenge_id,
                    'challenge_url': challenge_url,
                    'timestamp': datetime.now().isoformat(),
                    'data': {
                        'photo_id': entry_id,
                        'votes': entry.get('votes', 0),
                        'rank': current_data['rank']
                    }
                })
                logger.info(f"🔥 ANCA posted new photo {entry_id} in challenge {challenge_id}")
        
        # Detect swaps (disappeared entries)
        for entry_id in previous_entries:
            if entry_id not in current_entries:
                events.append({
                    'type': 'swap_out',
                    'challenge_id': challenge_id,
                    'challenge_url': challenge_url,
                    'timestamp': datetime.now().isoformat(),
                    'data': {
                        'photo_id': entry_id,
                        'previous_votes': previous_entries[entry_id].get('votes', 0),
                        'rank': current_data['rank']
                    }
                })
                logger.info(f"🔄 ANCA swapped out photo {entry_id} in challenge {challenge_id}")
        
        # Detect significant rank changes
        prev_rank = previous_data.get('rank', 0)
        curr_rank = current_data.get('rank', 0)
        
        if prev_rank > 0 and curr_rank > 0 and abs(curr_rank - prev_rank) >= 10:
            events.append({
                'type': 'rank_change',
                'challenge_id': challenge_id,
                'challenge_url': challenge_url,
                'timestamp': datetime.now().isoformat(),
                'data': {
                    'previous_rank': prev_rank,
                    'current_rank': curr_rank,
                    'rank_delta': curr_rank - prev_rank,
                    'votes': current_data['votes']
                }
            })
            logger.info(f"📈 ANCA rank changed from {prev_rank} to {curr_rank} in challenge {challenge_id}")
        
        return events
    
    async def _notify_anca_event(self, event: Dict):
        """Send WebSocket notification for ANCA event"""
        try:
            await connection_manager.broadcast_to_all({
                "type": "anca_surveillance_event",
                "event": event,
                "priority": "high" if event['type'] in ['new_entry', 'swap_out'] else "normal"
            })
        except Exception as e:
            logger.error(f"Error notifying ANCA event: {e}")
    
    def get_recent_events(self, limit: int = 50) -> List[Dict]:
        """Get recent ANCA events"""
        return self.events[-limit:]
    
    def get_stats(self) -> Dict:
        """Get ANCA surveillance statistics"""
        return {
            'total_events': len(self.events),
            'active_challenges': len(self.last_states),
            'event_types': {
                event_type: len([e for e in self.events if e['type'] == event_type])
                for event_type in ['first_detection', 'new_entry', 'swap_out', 'rank_change']
            }
        }

# Global instance
simple_anca_surveillance = SimpleAncaSurveillance()

# Cron job function (to be called by your cron MCP)
async def anca_surveillance_cron_job(user_token: str = None):
    """
    Cron job function for ANCA surveillance
    Call this every 5-15 minutes with: 
    
    @cron("*/10 * * * *")  # Every 10 minutes
    """
    if not user_token:
        # Get default user token from config
        users = config_manager.get_all_users()
        if users:
            user_token = list(users.values())[0].get('xtoken')
    
    if user_token:
        results = await simple_anca_surveillance.monitor_active_challenges(user_token)
        return results
    else:
        logger.error("No user token available for ANCA surveillance")
        return {"error": "No user token"}
