"""
Extended Strategy Executor
Supports new actions: submit, swap, boost, turbo (set_turbo)
Reads from strategies.ini format like [4photos]
"""

import re
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from configobj import ConfigObj

from app.services.gurushots_api import GuruShotsAPI
from app.services.config_manager import config_manager
from app.websockets.connection_manager import connection_manager

logger = logging.getLogger(__name__)

class ExtendedStrategyExecutor:
    """
    Executor for extended strategies with new actions
    """
    
    def __init__(self):
        self.strategies_config = ConfigObj('strategies.ini')
        self.active_executions = {}  # strategy_id -> execution context
    
    async def execute_extended_strategy(self, profile_id: str, challenge_id: str, 
                                      challenge_url: str, strategy_name: str) -> str:
        """Execute an extended strategy with timing"""
        
        if strategy_name not in self.strategies_config:
            raise ValueError(f"Strategy '{strategy_name}' not found in strategies.ini")
        
        # Get user token
        user = config_manager.get_user(profile_id)
        if not user or not user.get('xtoken'):
            raise ValueError(f"No valid user token for profile {profile_id}")
        
        # Create API client
        api_client = GuruShotsAPI(user['xtoken'])
        
        # Get challenge end time
        challenge_details = await api_client.get_challenge_details(challenge_url)
        challenge_end_time = datetime.fromtimestamp(
            challenge_details.get('challenge', {}).get('close_time', 0)
        )
        
        if challenge_end_time <= datetime.now():
            raise ValueError("Challenge has already ended")
        
        # Parse strategy actions
        actions = self._parse_strategy_actions(strategy_name, challenge_end_time)
        
        # Create execution context
        execution_id = f"{strategy_name}_{challenge_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        self.active_executions[execution_id] = {
            'profile_id': profile_id,
            'challenge_id': challenge_id,
            'challenge_url': challenge_url,
            'strategy_name': strategy_name,
            'challenge_end_time': challenge_end_time,
            'actions': actions,
            'started_at': datetime.now(),
            'status': 'active',
            'api_client': api_client
        }
        
        # Start execution task
        asyncio.create_task(self._execute_strategy_loop(execution_id))
        
        logger.info(f"🎯 Started extended strategy '{strategy_name}' with {len(actions)} actions")
        
        return execution_id
    
    def _parse_strategy_actions(self, strategy_name: str, challenge_end_time: datetime) -> List[Dict]:
        """Parse strategy actions from strategies.ini"""
        actions = []
        strategy_config = self.strategies_config[strategy_name]
        
        for step, action_string in strategy_config.items():
            if step == 'description':
                continue
            
            # Parse: "action, timing, param1, param2, ..."
            parts = [p.strip() for p in action_string.split(',')]
            
            if len(parts) < 2:
                logger.warning(f"Invalid action format: {action_string}")
                continue
            
            action = parts[0]
            timing = parts[1]
            parameters = parts[2:] if len(parts) > 2 else []
            
            # Calculate scheduled time
            scheduled_time = self._calculate_scheduled_time(timing, challenge_end_time)
            
            if scheduled_time:
                actions.append({
                    'step': int(step),
                    'action': action,
                    'timing': timing,
                    'parameters': parameters,
                    'scheduled_time': scheduled_time,
                    'executed': False,
                    'result': None
                })\n        
        # Sort by scheduled time
        actions.sort(key=lambda a: a['scheduled_time'])
        return actions
    
    def _calculate_scheduled_time(self, timing: str, challenge_end_time: datetime) -> Optional[datetime]:
        """Calculate when to execute based on timing specification"""
        if timing.lower() == 'now':
            return datetime.now()
        
        # Parse end-XmYs format (e.g., end-120m0s, end-90m0s)
        end_match = re.match(r'end-(\d+)m(\d+)s', timing)
        if end_match:
            minutes, seconds = int(end_match.group(1)), int(end_match.group(2))
            delta = timedelta(minutes=minutes, seconds=seconds)
            return challenge_end_time - delta
        
        logger.warning(f"Could not parse timing: {timing}")
        return None
    
    async def _execute_strategy_loop(self, execution_id: str):
        """Main execution loop for a strategy"""
        context = self.active_executions[execution_id]
        actions = context['actions']
        
        logger.info(f"🔄 Strategy execution started for {execution_id}")
        
        try:
            for action in actions:
                if context['status'] != 'active':
                    break
                
                # Wait until scheduled time
                now = datetime.now()
                if action['scheduled_time'] > now:
                    wait_seconds = (action['scheduled_time'] - now).total_seconds()
                    logger.info(f"⏰ Waiting {wait_seconds:.0f}s for {action['action']} action")
                    await asyncio.sleep(wait_seconds)
                
                # Check if still active
                if context['status'] != 'active':
                    break
                
                # Execute action
                try:
                    result = await self._execute_action(execution_id, action)
                    action['executed'] = True
                    action['result'] = result
                    
                    # Notify action completion
                    await self._notify_action_result(execution_id, action, result)
                    
                except Exception as e:
                    logger.error(f"Error executing {action['action']}: {str(e)}")
                    action['result'] = {'success': False, 'error': str(e)}
            
            # Mark as completed
            context['status'] = 'completed'
            logger.info(f"✅ Strategy {execution_id} completed")
            
        except Exception as e:
            logger.error(f"Strategy execution failed: {str(e)}")
            context['status'] = 'failed'
        
        finally:
            # Cleanup after delay
            await asyncio.sleep(300)  # Keep for 5 minutes
            if execution_id in self.active_executions:
                del self.active_executions[execution_id]
    
    async def _execute_action(self, execution_id: str, action: Dict) -> Dict[str, Any]:
        """Execute a single action"""
        context = self.active_executions[execution_id]
        api_client = context['api_client']
        challenge_id = int(context['challenge_id'])
        challenge_url = context['challenge_url']
        
        action_type = action['action']
        params = action['parameters']
        
        logger.info(f"🔧 Executing {action_type} with params {params}")
        
        try:
            if action_type == 'vote':
                return await self._execute_vote_action(api_client, challenge_url, params)
            
            elif action_type == 'submit':
                return await self._execute_submit_action(api_client, challenge_id, params)
            
            elif action_type == 'swap':
                return await self._execute_swap_action(api_client, challenge_id, params)
            
            elif action_type == 'boost':
                return await self._execute_boost_action(api_client, challenge_id, challenge_url, params)
            
            elif action_type == 'turbo':
                return await self._execute_turbo_action(api_client, challenge_id, params)
            
            else:
                return {'success': False, 'error': f'Unknown action: {action_type}'}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _execute_vote_action(self, api_client: GuruShotsAPI, challenge_url: str, params: List[str]) -> Dict:
        """Execute vote action"""
        if not params:
            return {'success': False, 'error': 'Vote count required'}
        
        try:
            vote_count = int(params[0])
            result = await api_client.execute_simple_vote(challenge_url, vote_count)
            return result
        except ValueError:
            return {'success': False, 'error': 'Invalid vote count'}
    
    async def _execute_submit_action(self, api_client: GuruShotsAPI, challenge_id: int, params: List[str]) -> Dict:
        """Execute submit action"""
        if not params:
            return {'success': False, 'error': 'Image ID(s) required for submit'}
        
        # Support multiple image IDs for multi-submit
        image_ids = params
        results = []
        
        for image_id in image_ids:
            try:
                # This would use the new submit method you added
                result = await api_client.submit_to_challenge(challenge_id, image_id)
                results.append({'image_id': image_id, 'result': result})
                logger.info(f"📸 Submitted image {image_id} to challenge {challenge_id}")
            except Exception as e:
                results.append({'image_id': image_id, 'error': str(e)})
        
        return {'success': True, 'submissions': results}
    
    async def _execute_swap_action(self, api_client: GuruShotsAPI, challenge_id: int, params: List[str]) -> Dict:
        """Execute swap action"""
        if len(params) < 2:
            return {'success': False, 'error': 'Two image IDs required for swap'}
        
        current_photo_id, new_photo_id = params[0], params[1]
        result = await api_client.swap_photo(challenge_id, current_photo_id, new_photo_id)
        
        logger.info(f"🔄 Swapped {current_photo_id} -> {new_photo_id} in challenge {challenge_id}")
        return result
    
    async def _execute_boost_action(self, api_client: GuruShotsAPI, challenge_id: int, 
                              challenge_url: str, params: List[str]) -> Dict:
        """Execute boost action with index support"""
        if not params:
            return {'success': False, 'error': 'Image ID or index required for boost'}
        
        param = params[0].strip()
        image_id = None
        
        # Handle index notation like [0] (photo with most votes) or just 0
        if param.startswith('[') and param.endswith(']'):
            # Remove brackets: [0] -> 0
            index_str = param[1:-1]
        else:
            index_str = param
        
        # Check if it's a numeric index
        if index_str.isdigit():
            index = int(index_str)
            logger.info(f"🔍 Resolving photo index [{index}] for boost action")
            
            image_id = await self._resolve_photo_by_index(api_client, challenge_id, index)
            if not image_id:
                return {
                    'success': False, 
                    'error': f'Could not resolve photo index [{index}]. User may not have photos in challenge or index out of range.'
                }
            
            logger.info(f"✅ Resolved index [{index}] to photo ID: {image_id}")
        else:
            # Direct image ID provided
            image_id = param
            logger.info(f"📸 Using direct photo ID: {image_id}")
        
        try:
            # Use the boost method (assuming you added this to GuruShotsAPI)
            result = await api_client.boost_photo(challenge_id, image_id)
            
            if result.get('success', True):  # Assume success if not explicitly failed
                logger.info(f"⚡ Successfully boosted photo {image_id} in challenge {challenge_id}")
                return {
                    'success': True,
                    'message': f'Boosted photo {image_id}',
                    'image_id': image_id,
                    'resolved_from_index': index_str if index_str.isdigit() else None
                }
            else:
                error_msg = result.get('error', 'Boost failed')
                logger.error(f"❌ Boost failed: {error_msg}")
                return {'success': False, 'error': error_msg, 'image_id': image_id}
                
        except Exception as e:
            logger.error(f"❌ Exception during boost: {str(e)}")
            return {'success': False, 'error': str(e), 'image_id': image_id}
    
    async def _execute_turbo_action(self, api_client: GuruShotsAPI, challenge_id: int, params: List[str]) -> Dict:
        """Execute turbo action using set_turbo (unlock turbo) with optional photo index"""
        try:
            # Check if a photo index is specified for targeting
            target_photo_id = None
            if params and params[0].strip():
                param = params[0].strip()
                
                # Handle index notation
                if param.startswith('[') and param.endswith(']'):
                    index_str = param[1:-1]
                else:
                    index_str = param
                
                if index_str.isdigit():
                    index = int(index_str)
                    logger.info(f"🎯 Resolving photo index [{index}] for turbo targeting")
                    
                    target_photo_id = await self._resolve_photo_by_index(api_client, challenge_id, index)
                    if target_photo_id:
                        logger.info(f"✅ Turbo will target photo {target_photo_id} (index [{index}])")
                    else:
                        logger.warning(f"⚠️ Could not resolve photo index [{index}], proceeding with general turbo")
                else:
                    target_photo_id = param
                    logger.info(f"🎯 Turbo will target specific photo: {target_photo_id}")
            
            # Use set_turbo method (unlock turbo)
            # Note: set_turbo might not support targeting specific photos, 
            # but we log the intention for future enhancement
            result = await api_client.set_turbo(challenge_id)
            
            if result.get('success', True):
                logger.info(f"🚀 Successfully unlocked turbo for challenge {challenge_id}")
                return {
                    'success': True,
                    'message': f'Unlocked turbo for challenge {challenge_id}',
                    'challenge_id': challenge_id,
                    'target_photo_id': target_photo_id,
                    'note': 'Turbo unlocked - specific photo targeting may require additional implementation'
                }
            else:
                error_msg = result.get('error', 'Turbo unlock failed')
                logger.error(f"❌ Turbo unlock failed: {error_msg}")
                return {'success': False, 'error': error_msg}
                
        except Exception as e:
            logger.error(f"❌ Exception during turbo unlock: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def _resolve_photo_by_index(self, api_client: GuruShotsAPI, challenge_id: int, index: int) -> Optional[str]:
        """Resolve photo ID by index (0=most votes, 1=second most, etc.)"""
        try:
            # Get current user info to identify them in ranking
            current_user_info = await self._get_current_user_info(api_client)
            if not current_user_info:
                logger.error("Could not identify current user")
                return None
            
            current_username = current_user_info.get('username', '').lower()
            current_user_id = current_user_info.get('user_id')
            
            logger.info(f"Resolving photo index {index} for user {current_username}")
            
            # Get challenge ranking to find user's photos
            ranking = await api_client.get_challenge_followings(challenge_id, limit=500)
            
            if not ranking.get('items'):
                logger.error("No ranking data available")
                return None
            
            # Find current user in ranking
            user_data = None
            for participant in ranking['items']:
                member = participant.get('member', {})
                participant_username = member.get('user_name', '').lower()
                participant_user_id = member.get('id')
                
                # Match by username or user_id
                if ((current_username and participant_username == current_username) or 
                    (current_user_id and participant_user_id == current_user_id)):
                    user_data = participant
                    break
            
            if not user_data:
                logger.error(f"Current user not found in challenge {challenge_id} ranking")
                return None
            
            # Get user's photos/entries
            entries = user_data.get('entries', [])
            if not entries:
                logger.error("User has no photos in this challenge")
                return None
            
            # Sort entries by votes (descending: most votes first)
            sorted_entries = sorted(entries, key=lambda x: x.get('votes', 0), reverse=True)
            
            # Check if index is valid
            if index < 0 or index >= len(sorted_entries):
                logger.error(f"Photo index {index} out of range (user has {len(sorted_entries)} photos)")
                return None
            
            # Get photo ID at requested index
            selected_photo = sorted_entries[index]
            photo_id = selected_photo['id']
            photo_votes = selected_photo.get('votes', 0)
            
            logger.info(f"✅ Resolved index [{index}] -> photo {photo_id} with {photo_votes} votes")
            
            return photo_id
            
        except Exception as e:
            logger.error(f"Error resolving photo index {index}: {e}")
            return None

    async def _get_current_user_info(self, api_client: GuruShotsAPI) -> Optional[Dict]:
        """Get current user information"""
        try:
            user_info = await api_client.get_current_user_info()
            
            if user_info and user_info.get('user_id'):
                return user_info
            else:
                logger.error("Failed to retrieve current user information")
                return None
                
        except Exception as e:
            logger.error(f"Error getting current user info: {e}")
            return None

    async def _get_current_user_info(self, api_client: GuruShotsAPI) -> Optional[Dict[str, Any]]:
        """Get current user information to identify them in rankings"""
        try:
            # Method 1: Try to get user info from challenges page
            # This is a common pattern in GuruShots API
            challenges_response = await api_client.get_challenges()
            
            # Look for user info in challenges response
            if challenges_response and 'user' in challenges_response:
                user_info = challenges_response['user']
                return {
                    'username': user_info.get('username', ''),
                    'user_id': user_info.get('id'),
                    'name': user_info.get('name', '')
                }
            
            # Method 2: Try to get user profile via a dummy challenge detail call
            # Some APIs return user info in the member section
            challenges = challenges_response.get('challenges', [])
            if challenges:
                # Take first challenge and get its details
                first_challenge_url = challenges[0].get('url', '')
                if first_challenge_url:
                    challenge_details = await api_client.get_challenge_details(first_challenge_url)
                    
                    # Look for current user info in challenge details
                    challenge_data = challenge_details.get('challenge', {})
                    member_data = challenge_data.get('member', {})
                    
                    if member_data:
                        return {
                            'username': member_data.get('user_name', ''),
                            'user_id': member_data.get('id'),
                            'name': member_data.get('name', '')
                        }
            
            # Method 3: Fallback - try to extract from API base response
            # Some GuruShots endpoints include user context
            logger.warning("Could not determine current user info from standard endpoints")
            return None
            
        except Exception as e:
            logger.error(f"Error getting current user info: {e}")
            return None

    async def test_photo_index_resolution(self, profile_id: str, challenge_id: int) -> Dict:
        """
        Test photo index resolution for a given challenge
        Returns user's photos sorted by votes with their indices
        """
        try:
            # Get user and API client
            user = config_manager.get_user(profile_id)
            if not user or not user.get('xtoken'):
                return {'success': False, 'error': f'No valid user token for profile {profile_id}'}
            
            api_client = GuruShotsAPI(user['xtoken'])
            
            # Get current user info
            user_info = await self._get_current_user_info(api_client)
            if not user_info:
                return {'success': False, 'error': 'Could not identify current user'}
            
            # Get challenge ranking
            ranking = await api_client.get_challenge_followings(challenge_id, limit=500)
            if not ranking.get('items'):
                return {'success': False, 'error': 'No ranking data available'}
            
            # Find user in ranking
            current_username = user_info.get('username', '').lower()
            current_user_id = user_info.get('user_id')
            
            user_data = None
            for participant in ranking['items']:
                member = participant.get('member', {})
                participant_username = member.get('user_name', '').lower()
                participant_user_id = member.get('id')
                
                if ((current_username and participant_username == current_username) or 
                    (current_user_id and participant_user_id == current_user_id)):
                    user_data = participant
                    break
            
            if not user_data:
                return {'success': False, 'error': 'User not found in challenge ranking'}
            
            # Get and sort user's photos
            entries = user_data.get('entries', [])
            if not entries:
                return {'success': False, 'error': 'User has no photos in this challenge'}
            
            sorted_entries = sorted(entries, key=lambda x: x.get('votes', 0), reverse=True)
            
            # Format result with indices
            photos_with_indices = []
            for i, entry in enumerate(sorted_entries):
                photos_with_indices.append({
                    'index': i,
                    'photo_id': entry['id'],
                    'votes': entry.get('votes', 0),
                    'boost_status': entry.get('boost', False),
                    'guru_pick': entry.get('guru_pick', False)
                })
            
            return {
                'success': True,
                'user_info': {
                    'username': user_info.get('username'),
                    'user_id': user_info.get('user_id'),
                    'total_rank': user_data.get('total', {}).get('rank', 0),
                    'total_votes': user_data.get('total', {}).get('votes', 0)
                },
                'photos': photos_with_indices,
                'index_explanation': {
                    '[0]': f"Photo with most votes: {photos_with_indices[0]['photo_id']} ({photos_with_indices[0]['votes']} votes)" if photos_with_indices else "No photos",
                    '[1]': f"Photo with second most votes: {photos_with_indices[1]['photo_id']} ({photos_with_indices[1]['votes']} votes)" if len(photos_with_indices) > 1 else "Only one photo available"
                }
            }
            
        except Exception as e:
            logger.error(f"Error testing photo index resolution: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _get_user_photos_sorted_by_votes(self, api_client: GuruShotsAPI, 
                                             challenge_id: int) -> List[Dict[str, Any]]:
        """Get current user's photos in challenge sorted by votes (most votes first)"""
        try:
            current_user_info = await self._get_current_user_info(api_client)
            if not current_user_info:
                return []
            
            # Get challenge ranking
            ranking = await api_client.get_challenge_followings(challenge_id, limit=500)
            
            # Find current user and return sorted photos
            current_username = current_user_info.get('username', '').lower()
            current_user_id = current_user_info.get('user_id')
            
            for participant in ranking.get('items', []):
                member = participant.get('member', {})
                participant_username = member.get('user_name', '').lower()
                participant_user_id = member.get('id')
                
                if (current_username and participant_username == current_username) or \
                   (current_user_id and participant_user_id == current_user_id):
                    
                    entries = participant.get('entries', [])
                    # Sort by votes (descending)
                    sorted_entries = sorted(entries, key=lambda x: x.get('votes', 0), reverse=True)
                    
                    # Add index information for logging
                    for i, entry in enumerate(sorted_entries):
                        entry['_index'] = i
                        entry['_votes_rank'] = i + 1
                    
                    return sorted_entries
            
            return []
            
        except Exception as e:
            logger.error(f"Error getting user photos sorted by votes: {e}")
            return []
    
    async def _notify_action_result(self, execution_id: str, action: Dict, result: Dict):
        """Notify action completion via WebSocket"""
        context = self.active_executions[execution_id]
        
        await connection_manager.broadcast_to_all({
            "type": "extended_strategy_action",
            "execution_id": execution_id,
            "challenge_id": context['challenge_id'],
            "strategy_name": context['strategy_name'],
            "action": {
                'step': action['step'],
                'action': action['action'],
                'timing': action['timing'],
                'parameters': action['parameters'],
                'result': result
            }
        })
    
    def get_execution_status(self, execution_id: str) -> Optional[Dict]:
        """Get status of strategy execution"""
        if execution_id not in self.active_executions:
            return None
        
        context = self.active_executions[execution_id]
        actions = context['actions']
        
        return {
            'execution_id': execution_id,
            'strategy_name': context['strategy_name'],
            'challenge_id': context['challenge_id'],
            'status': context['status'],
            'started_at': context['started_at'].isoformat(),
            'total_actions': len(actions),
            'completed_actions': sum(1 for a in actions if a['executed']),
            'next_action': next((a for a in actions if not a['executed']), None)
        }
    
    async def cancel_execution(self, execution_id: str) -> bool:
        """Cancel strategy execution"""
        if execution_id in self.active_executions:
            self.active_executions[execution_id]['status'] = 'cancelled'
            logger.info(f"❌ Strategy execution {execution_id} cancelled")
            return True
        return False

# Global instance
extended_strategy_executor = ExtendedStrategyExecutor()
