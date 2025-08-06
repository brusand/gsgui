"""
Competitor Tracking Service for GuruShots
Tracks following users in challenges and detects events (swaps, posts, boosts)
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional
from configobj import ConfigObj
import aiohttp

from app.websockets.connection_manager import connection_manager

logger = logging.getLogger(__name__)

class CompetitorTracker:
    """
    Service for tracking competitor activities in GuruShots challenges
    Implements ANCA-style competitor surveillance strategies
    """
    
    def __init__(self, gurushots_api, user_id: str = "default_user"):
        self.api = gurushots_api
        self.user_id = user_id  # User to notify via WebSocket
        self.tracking_sessions = {}  # challenge_id -> tracking session
        self.competitor_data = {}    # challenge_id -> competitor data
        
    async def start_tracking_challenge(self, challenge_id: int, challenge_url: str, 
                                     competitors: List[str] = None) -> bool:
        """
        Start tracking competitors in a challenge
        
        Args:
            challenge_id: Challenge ID to track
            challenge_url: Challenge URL 
            competitors: List of specific competitors to track (optional)
            
        Returns:
            True if tracking started successfully
        """
        if challenge_id in self.tracking_sessions:
            logger.warning(f"Already tracking challenge {challenge_id}")
            return False
            
        try:
            # Initialize tracking session
            self.tracking_sessions[challenge_id] = {
                'active': True,
                'url': challenge_url,
                'competitors': competitors or [],
                'start_time': datetime.now(),
                'last_update': None
            }
            
            # Initialize competitor data storage
            self.competitor_data[challenge_id] = {}
            
            # Start tracking loop
            asyncio.create_task(self._tracking_loop(challenge_id))
            
            logger.info(f"Started tracking challenge {challenge_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error starting tracking for challenge {challenge_id}: {str(e)}")
            return False
    
    async def stop_tracking_challenge(self, challenge_id: int):
        """Stop tracking a challenge"""
        if challenge_id in self.tracking_sessions:
            self.tracking_sessions[challenge_id]['active'] = False
            logger.info(f"Stopped tracking challenge {challenge_id}")
    
    async def _tracking_loop(self, challenge_id: int):
        """Main tracking loop for a challenge"""
        session = self.tracking_sessions[challenge_id]
        
        while session['active']:
            try:
                await self._update_competitor_data(challenge_id)
                session['last_update'] = datetime.now()
                
                # Check challenge status
                challenge_details = await self.api.get_challenge_details(session['url'])
                if challenge_details.get('challenge', {}).get('close_time', 0) == 0:
                    logger.info(f"Challenge {challenge_id} closed, stopping tracking")
                    break
                    
                # Adjust polling frequency based on time left
                timeleft = challenge_details.get('challenge', {}).get('time_left', {})
                if timeleft.get('days', 0) == 0 and timeleft.get('hours', 0) == 0:
                    # Last hour - poll every minute
                    await asyncio.sleep(60)
                elif timeleft.get('days', 0) == 0:
                    # Last day - poll every 5 minutes  
                    await asyncio.sleep(300)
                else:
                    # Earlier - poll every 15 minutes
                    await asyncio.sleep(900)
                    
            except Exception as e:
                logger.error(f"Error in tracking loop for challenge {challenge_id}: {str(e)}")
                await asyncio.sleep(60)  # Wait before retrying
        
        # Cleanup
        session['active'] = False
        logger.info(f"Tracking loop ended for challenge {challenge_id}")
    
    async def _update_competitor_data(self, challenge_id: int):
        """Update competitor data for a challenge"""
        try:
            # Get current followings in challenge
            followings_data = await self.api.get_challenge_followings(challenge_id)
            
            if not followings_data.get('success', True):
                logger.warning(f"Failed to get followings for challenge {challenge_id}")
                return
            
            current_time = datetime.now().isoformat()
            
            for following in followings_data.get('items', []):
                user_name = following['member']['user_name']
                user_id = following['member']['id']
                
                # Initialize user data if not exists
                if user_name not in self.competitor_data[challenge_id]:
                    self.competitor_data[challenge_id][user_name] = {
                        'user_id': user_id,
                        'name': following['member']['name'],
                        'entries': {},
                        'events': [],
                        'stats': {
                            'swaps': 0,
                            'posts': 0, 
                            'boosts': 0
                        }
                    }
                
                # Detect events by comparing current vs previous entries
                await self._detect_events(challenge_id, user_name, following, current_time)
                
        except Exception as e:
            logger.error(f"Error updating competitor data: {str(e)}")
    
    async def _detect_events(self, challenge_id: int, user_name: str, 
                           following: dict, current_time: str):
        """Detect competitor events (swaps, posts, boosts)"""
        competitor = self.competitor_data[challenge_id][user_name]
        current_entries = {entry['id']: entry for entry in following.get('entries', [])}
        previous_entries = competitor['entries']
        
        # Detect new posts
        for entry_id, entry in current_entries.items():
            if entry_id not in previous_entries:
                event = {
                    'type': 'post',
                    'photo_id': entry_id,
                    'timestamp': current_time,
                    'votes': entry.get('votes', 0),
                    'rank': following.get('total', {}).get('rank', 0)
                }
                competitor['events'].append(event)
                competitor['stats']['posts'] += 1
                logger.info(f"🔥 {user_name} posted new photo {entry_id} in challenge {challenge_id}")
                
                # Notify via WebSocket
                await connection_manager.notify_competitor_event(
                    self.user_id, challenge_id, user_name, "post", event
                )
                
                # Special notification for ANCA or other tracked competitors
                if "anca" in user_name.lower() or "vampire" in user_name.lower():
                    await connection_manager.notify_anca_activity(
                        self.user_id, challenge_id, user_name, "post", event
                    )
        
        # Detect swaps (photos that disappeared)
        for entry_id in previous_entries:
            if entry_id not in current_entries:
                event = {
                    'type': 'swap_out',
                    'photo_id': entry_id,
                    'timestamp': current_time,
                    'previous_votes': previous_entries[entry_id].get('votes', 0)
                }
                competitor['events'].append(event)
                competitor['stats']['swaps'] += 1
                logger.info(f"🔄 {user_name} swapped out photo {entry_id} in challenge {challenge_id}")
                
                # Notify via WebSocket
                await connection_manager.notify_competitor_event(
                    self.user_id, challenge_id, user_name, "swap_out", event
                )
                
                # Special notification for ANCA or other tracked competitors
                if "anca" in user_name.lower() or "vampire" in user_name.lower():
                    await connection_manager.notify_anca_activity(
                        self.user_id, challenge_id, user_name, "swap", event
                    )
        
        # Detect boosts
        for entry_id, entry in current_entries.items():
            if entry_id in previous_entries:
                prev_boost = previous_entries[entry_id].get('boost', False)
                curr_boost = entry.get('boost', False)
                
                if not prev_boost and curr_boost:
                    event = {
                        'type': 'boost',
                        'photo_id': entry_id,
                        'timestamp': current_time,
                        'votes': entry.get('votes', 0)
                    }
                    competitor['events'].append(event)
                    competitor['stats']['boosts'] += 1
                    logger.info(f"⚡ {user_name} boosted photo {entry_id} in challenge {challenge_id}")
                    
                    # Notify via WebSocket
                    await connection_manager.notify_competitor_event(
                        self.user_id, challenge_id, user_name, "boost", event
                    )
                    
                    # Special notification for ANCA or other tracked competitors
                    if "anca" in user_name.lower() or "vampire" in user_name.lower():
                        await connection_manager.notify_anca_activity(
                            self.user_id, challenge_id, user_name, "boost", event
                        )
        
        # Update stored entries
        competitor['entries'] = current_entries
    
    def get_competitor_data(self, challenge_id: int, user_name: str = None) -> dict:
        """Get competitor data for a challenge"""
        if challenge_id not in self.competitor_data:
            return {}
            
        if user_name:
            return self.competitor_data[challenge_id].get(user_name, {})
        else:
            return self.competitor_data[challenge_id]
    
    def get_tracking_status(self) -> dict:
        """Get status of all tracking sessions"""
        status = {}
        for challenge_id, session in self.tracking_sessions.items():
            status[challenge_id] = {
                'active': session['active'],
                'url': session['url'],
                'competitors_count': len(self.competitor_data.get(challenge_id, {})),
                'start_time': session['start_time'].isoformat(),
                'last_update': session['last_update'].isoformat() if session['last_update'] else None
            }
        return status

# Global instance
competitor_tracker = None

def get_competitor_tracker(gurushots_api, user_id: str = "default_user") -> CompetitorTracker:
    """Get or create competitor tracker instance"""
    global competitor_tracker
    if competitor_tracker is None:
        competitor_tracker = CompetitorTracker(gurushots_api, user_id)
    return competitor_tracker
