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
from xmlrpc.client import boolean

from configobj import ConfigObj

from app.services.gurushots_api import GuruShotsAPI
from app.services.config_manager import config_manager
from app.websockets.connection_manager import connection_manager
# Import needed for WebSocket logging to frontend
try:
    from app.utils.logging_utils import log_and_broadcast
except ImportError:
    # Fallback si pas disponible
    def log_and_broadcast(message, level="info", profile_id=None, challenge_id=None, **kwargs):
        from datetime import datetime
        
        # Ajouter horodatage et profile_id au message
        timestamp = datetime.now().strftime("%H:%M:%S")
        if profile_id:
            formatted_message = f"[{timestamp}] [{profile_id}] {message}"
        else:
            formatted_message = f"[{timestamp}] {message}"
            
        logger.info(formatted_message)
        
        # Diffuser via WebSocket si possible
        try:
            import asyncio
            from app.websockets.connection_manager import connection_manager
            
            # Diffuser aux WebSockets par profil
            if profile_id:
                asyncio.create_task(connection_manager.notify_broadcast_log(
                    profile_id, level, formatted_message))
        except (ImportError, RuntimeError):
            # Si pas de WebSocket ou de loop actif, ignorer la diffusion
            pass
        
try:
    from app.utils.logging_utils import get_challenge_title_from_cache
except ImportError:
    def get_challenge_title_from_cache(challenge_id):
        return challenge_id

logger = logging.getLogger(__name__)

class ExtendedStrategyExecutor:
    """
    Executor for extended strategies with new actions
    """
    
    def __init__(self):
        # Path relatif depuis le répertoire backend/
        self.strategies_config = ConfigObj('data/strategies.ini')
        self.active_executions = {}  # strategy_id -> execution context
    
    def reload_config(self):
        """Recharge la configuration des stratégies depuis le fichier strategies.ini"""
        try:
            logger.info("🔄 Rechargement de la configuration strategies.ini...")
            self.strategies_config = ConfigObj('data/strategies.ini')
            logger.info(f"✅ Configuration rechargée: {len(self.strategies_config)} stratégies disponibles")
            return True
        except Exception as e:
            logger.error(f"❌ Erreur lors du rechargement de la configuration: {e}")
            return False
    
    async def execute_extended_strategy(self, profile_id: str, challenge_id: str, 
                                      challenge_url: str, strategy_name: str) -> str:
        """Execute an extended strategy with timing - separates NOW vs FUTURE actions"""
        
        if strategy_name not in self.strategies_config:
            raise ValueError(f"Strategy '{strategy_name}' not found in strategies.ini")
        
        # Get user token
        user = config_manager.get_user(profile_id)
        if not user or not user.get('xtoken'):
            raise ValueError(f"No valid user token for profile {profile_id}")
        
        # Create API client
        api_client = GuruShotsAPI(user['xtoken'])
        
        # Get challenge end time from get_challenges() instead of get_challenge_details()
        challenge_end_time = await self._get_challenge_end_time(api_client, challenge_id)
        
        if challenge_end_time <= datetime.now():
            raise ValueError("Challenge has already ended")
        
        # Parse strategy actions
        actions = self._parse_strategy_actions(strategy_name, challenge_end_time)
        
        # Separate NOW actions from FUTURE actions
        now_actions = [a for a in actions if a.get('timing') == 'now']
        future_actions = [a for a in actions if a.get('timing') != 'now']
        
        # Execute NOW actions immediately
        now_results = []
        if now_actions:
            logger.info(f"⚡ Executing {len(now_actions)} immediate actions for strategy '{strategy_name}'")
            for action in now_actions:
                try:
                    result = await self._execute_single_action(api_client, challenge_id, challenge_url, action, profile_id)
                    now_results.append(result)
                    logger.info(f"✅ Immediate action {action['action']} completed: {result.get('success', False)}")
                except Exception as e:
                    logger.error(f"❌ Immediate action {action['action']} failed: {e}")
                    now_results.append({'success': False, 'error': str(e)})
        
        # Handle FUTURE actions if any - utiliser APScheduler
        execution_id = f"{strategy_name}_{challenge_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        if future_actions:
            self.active_executions[execution_id] = {
                'profile_id': profile_id,
                'challenge_id': challenge_id,
                'challenge_url': challenge_url,
                'strategy_name': strategy_name,
                'challenge_end_time': challenge_end_time,
                'actions': future_actions,
                'started_at': datetime.now(),
                'status': 'active',
                'api_client': api_client
            }
            
            # Programmer chaque action future via APScheduler
            await self._schedule_future_actions_with_apscheduler(execution_id, future_actions)
            logger.info(f"📅 Scheduled {len(future_actions)} future actions via APScheduler for strategy '{strategy_name}'")
        
        logger.info(f"🎯 Strategy '{strategy_name}' started: {len(now_actions)} immediate + {len(future_actions)} scheduled actions")
        
        # Si TOUTES les actions sont immédiates (pas d'actions futures), cleanup immédiatement
        # IMPORTANT: Cleanup même si certaines actions ont échoué, car elles ont été tentées
        if now_actions and not future_actions:
            logger.info(f"🧹 Toutes les actions sont immédiates, cleanup immédiat pour challenge {challenge_id}")
            await self._cleanup_completed_strategy(challenge_id, profile_id)
        elif now_actions and future_actions:
            logger.info(f"📝 Actions mixtes: {len(now_actions)} immédiates + {len(future_actions)} futures - cleanup après actions futures")
        elif not now_actions and future_actions:
            logger.info(f"📅 Seulement actions futures: {len(future_actions)} - cleanup après exécution")
        else:
            logger.info(f"⚠️  Aucune action valide trouvée pour '{strategy_name}' - cleanup immédiat")
            await self._cleanup_completed_strategy(challenge_id, profile_id)
        
        return execution_id
    
    async def _execute_single_action(self, api_client: GuruShotsAPI, challenge_id: str, challenge_url: str, action: Dict, profile_id: str) -> Dict[str, Any]:
        """Execute a single action immediately"""
        action_type = action['action']
        params = action['parameters']
        
        logger.info(f"⚡ Executing immediate {action_type} with params {params}")
        
        try:
            result = None
            if action_type == 'vote':
                result = await self._execute_vote_action(api_client, challenge_url, params, profile_id, str(challenge_id))
            
            elif action_type == 'submit':
                result = await self._execute_submit_action(api_client, int(challenge_id), params)
            
            elif action_type == 'swap':
                result = await self._execute_swap_action(api_client, int(challenge_id), params)
            
            elif action_type == 'boost':
                result = await self._execute_boost_action(api_client, int(challenge_id), challenge_url, params)
            
            elif action_type == 'turbo':
                result = await self._execute_turbo_action(api_client, int(challenge_id), challenge_url, params)

            elif action_type == 'unlocked_boost':
                result = await self._execute_unlocked_boost_action(api_client, int(challenge_id), challenge_url, params, profile_id)

            else:
                result = {'success': False, 'error': f'Unknown action: {action_type}'}
            
            # Déclencher un refresh du frontend pour les actions réussies
            if result and result.get('success', True):  # True par défaut si pas de champ success
                await connection_manager.notify_challenge_update(profile_id, {
                    "action": f"{action_type}_completed",
                    "challenge_id": challenge_id,
                    "strategy_type": "extended",
                    "immediate": True
                })
                logger.info(f"📡 Frontend refresh déclenché pour action {action_type} sur challenge {challenge_id}")
            
            return result
                
        except Exception as e:
            logger.error(f"Error executing {action_type}: {e}")
            return {'success': False, 'error': str(e)}
    
    def _is_timing_format(self, text: str) -> bool:
        """Check if text looks like a timing format"""
        timing_patterns = [
            r'end-\d+[mh]\d*s',     # end-4m0s, end-60m0s
            r'next-\d+[mh]\d*s',    # next-1m0s, next-2h0s
            r'now',                 # now
            r'end-\d+m\d*s',        # end-4m0s
            r'end-\d+h\d*m\d*s'     # end-1h30m0s
        ]
        
        for pattern in timing_patterns:
            if re.match(pattern, text, re.IGNORECASE):
                return True
        return False
    
    def _parse_strategy_actions(self, strategy_name: str, challenge_end_time: datetime) -> List[Dict]:
        """Parse strategy actions from strategies.ini - supports both formats"""
        actions = []
        strategy_config = self.strategies_config[strategy_name]
        
        for step, action_string in strategy_config.items():
            if step == 'description':
                continue
            
            # Parse: "action, timing, param1, param2, ..." OR "timing, param1, param2, ..." (vote implicite)
            parts = [p.strip() for p in action_string.split(',')]
            
            if len(parts) < 1:
                logger.warning(f"Invalid action format: {action_string}")
                continue
            
            # Detect format: if first part looks like timing, assume vote action
            first_part = parts[0]
            if self._is_timing_format(first_part):
                # Format: "timing, param1, param2, ..." - vote implicite
                action = 'vote'
                timing = first_part
                parameters = parts[1:] if len(parts) > 1 else []
            else:
                # Format: "action, timing, param1, param2, ..."
                if len(parts) < 2:
                    logger.warning(f"Invalid action format (missing timing): {action_string}")
                    continue
                action = first_part
                timing = parts[1]
                parameters = parts[2:] if len(parts) > 2 else []
            
            # Calculate scheduled time
            scheduled_time = self._calculate_scheduled_time(timing, challenge_end_time)
            
            if scheduled_time:
                actions.append({
                    'step': int(step),
                    'action': action,
                    'timing': timing,  # Original timing string for NOW detection
                    'parameters': parameters,
                    'scheduled_time': scheduled_time,
                    'executed': False,
                    'result': None
                })
        # Sort by scheduled time
        actions.sort(key=lambda a: a['scheduled_time'])
        return actions
    
    def _calculate_scheduled_time(self, timing: str, challenge_end_time: datetime) -> Optional[datetime]:
        """Calculate when to execute based on timing specification"""
        if timing.lower() == 'now':
            return datetime.now()
        
        # Parse end-XmYs format (e.g., end-120m0s, end-90m0s, end-4m0s)
        end_match = re.match(r'end-(\d+)m(\d+)s', timing)
        if end_match:
            minutes, seconds = int(end_match.group(1)), int(end_match.group(2))
            delta = timedelta(minutes=minutes, seconds=seconds)
            return challenge_end_time - delta
        
        # Parse end-XhYmZs format (e.g., end-1h30m0s)
        end_hour_match = re.match(r'end-(\d+)h(\d+)m(\d+)s', timing)
        if end_hour_match:
            hours, minutes, seconds = int(end_hour_match.group(1)), int(end_hour_match.group(2)), int(end_hour_match.group(3))
            delta = timedelta(hours=hours, minutes=minutes, seconds=seconds)
            return challenge_end_time - delta
        
        # Parse next-XmYs format (e.g., next-1m0s, next-2m0s) - from now
        next_match = re.match(r'next-(\d+)m(\d+)s', timing)
        if next_match:
            minutes, seconds = int(next_match.group(1)), int(next_match.group(2))
            delta = timedelta(minutes=minutes, seconds=seconds)
            return datetime.now() + delta
        
        # Parse next-XhYmZs format (e.g., next-1h30m0s)
        next_hour_match = re.match(r'next-(\d+)h(\d+)m(\d+)s', timing)
        if next_hour_match:
            hours, minutes, seconds = int(next_hour_match.group(1)), int(next_hour_match.group(2)), int(next_hour_match.group(3))
            delta = timedelta(hours=hours, minutes=minutes, seconds=seconds)
            return datetime.now() + delta
        
        logger.warning(f"Could not parse timing: {timing}")
        return None
    
    async def _schedule_future_actions_with_apscheduler(self, execution_id: str, future_actions: List[Dict]):
        """Programme les actions futures via APScheduler au lieu d'asyncio"""
        try:
            # Importer APScheduler
            from app.services.strategy_scheduler import strategy_scheduler
            
            if not strategy_scheduler._running:
                logger.error("❌ APScheduler not running, cannot schedule future actions")
                return
            
            # Programmer chaque action individuellement
            for i, action in enumerate(future_actions):
                job_id = f"extended_{execution_id}_action_{i}_{action['action']}"
                
                # Ajouter le job à APScheduler avec optimisations précision
                strategy_scheduler.scheduler.add_job(
                    func=self._execute_scheduled_action,
                    trigger='date',
                    run_date=action['scheduled_time'],
                    args=[execution_id, i],
                    id=job_id,
                    name=f"Extended {action['action']} for {execution_id}",
                    replace_existing=True,
                    # Optimisations précision critiques
                    coalesce=True,         # Fusionner si en retard
                    max_instances=1,       # Une seule instance
                    misfire_grace_time=3   # 3s de tolérance pour actions critiques
                )
                
                logger.info(f"📅 Scheduled action {action['action']} at {action['scheduled_time']} (job: {job_id})")
            
            logger.info(f"✅ All {len(future_actions)} actions scheduled via APScheduler")
            
        except Exception as e:
            logger.error(f"❌ Error scheduling actions via APScheduler: {e}")
            # Fallback sur l'ancienne méthode
            asyncio.create_task(self._execute_strategy_loop_fallback(execution_id))
    
    async def _execute_scheduled_action(self, execution_id: str, action_index: int):
        """Exécute une action programmée via APScheduler avec monitoring de précision"""
        execution_start_time = datetime.now()
        
        try:
            if execution_id not in self.active_executions:
                logger.warning(f"⚠️ Execution {execution_id} not found for scheduled action {action_index}")
                return
            
            context = self.active_executions[execution_id]
            if context['status'] != 'active':
                logger.info(f"⏹️ Execution {execution_id} no longer active, skipping action {action_index}")
                return
            
            actions = context['actions']
            if action_index >= len(actions):
                logger.error(f"❌ Action index {action_index} out of range for {execution_id}")
                return
            
            action = actions[action_index]
            
            # Vérifier la précision d'exécution
            expected_time = action.get('scheduled_time')
            if expected_time:
                delay = (execution_start_time - expected_time).total_seconds()
                if abs(delay) > 2:  # Plus de 2 secondes d'écart
                    logger.warning(f"⚠️ APScheduler precision issue: {delay:.2f}s delay for {action['action']} (expected: {expected_time.strftime('%H:%M:%S')}, actual: {execution_start_time.strftime('%H:%M:%S')})")
                else:
                    logger.info(f"✅ APScheduler precision OK: {delay:.2f}s delay for {action['action']}")
            
            # Marquer comme étant en cours d'exécution
            action['executing'] = True
            action['actual_execution_time'] = execution_start_time.isoformat()
            
            logger.info(f"🚀 Executing scheduled action {action['action']} for {execution_id} at {execution_start_time.strftime('%H:%M:%S.%f')}")
            
            # Exécuter l'action
            result = await self._execute_action(execution_id, action)
            action['executed'] = True
            action['result'] = result
            action['executing'] = False
            action['execution_duration'] = (datetime.now() - execution_start_time).total_seconds()
            
            logger.info(f"✅ Action {action['action']} completed in {action['execution_duration']:.2f}s")
            
            # Notifier la completion
            await self._notify_action_result(execution_id, action, result)
            
            # Vérifier si toutes les actions sont terminées
            await self._check_strategy_completion(execution_id)
            
        except Exception as e:
            logger.error(f"❌ Error executing scheduled action {action_index} for {execution_id}: {e}")
            # Marquer l'action comme échouée
            if execution_id in self.active_executions:
                context = self.active_executions[execution_id]
                if action_index < len(context['actions']):
                    context['actions'][action_index]['result'] = {'success': False, 'error': str(e)}
                    context['actions'][action_index]['executed'] = True
                    context['actions'][action_index]['executing'] = False
    
    async def _check_strategy_completion(self, execution_id: str):
        """Vérifie si toutes les actions d'une stratégie sont terminées"""
        try:
            if execution_id not in self.active_executions:
                return
            
            context = self.active_executions[execution_id]
            actions = context['actions']
            
            # Vérifier si toutes les actions sont exécutées
            all_executed = all(action.get('executed', False) for action in actions)
            
            if all_executed:
                # Marquer la stratégie comme terminée
                context['status'] = 'completed'
                logger.info(f"✅ Strategy {execution_id} completed - all actions executed")
                
                # Cleanup de la stratégie
                await self._cleanup_completed_strategy(context['challenge_id'], context['profile_id'])
                
                # Programmer la suppression de l'exécution après 5 minutes
                from app.services.strategy_scheduler import strategy_scheduler
                cleanup_job_id = f"cleanup_{execution_id}"
                strategy_scheduler.scheduler.add_job(
                    func=self._cleanup_execution_context,
                    trigger='date',
                    run_date=datetime.now() + timedelta(minutes=5),
                    args=[execution_id],
                    id=cleanup_job_id,
                    name=f"Cleanup {execution_id}",
                    replace_existing=True,
                    coalesce=True,
                    max_instances=1,
                    misfire_grace_time=30  # Cleanup moins critique
                )
                logger.info(f"📅 Scheduled cleanup for {execution_id} in 5 minutes")
            
        except Exception as e:
            logger.error(f"❌ Error checking strategy completion: {e}")
    
    def _cleanup_execution_context(self, execution_id: str):
        """Nettoie le contexte d'exécution (appelé par APScheduler)"""
        try:
            if execution_id in self.active_executions:
                del self.active_executions[execution_id]
                logger.info(f"🧹 Cleaned up execution context for {execution_id}")
        except Exception as e:
            logger.error(f"❌ Error cleaning up execution context {execution_id}: {e}")
    
    async def _execute_strategy_loop_fallback(self, execution_id: str):
        """Fallback execution loop si APScheduler échoue"""
        context = self.active_executions[execution_id]
        actions = context['actions']
        
        logger.info(f"🔄 Strategy execution started (fallback) for {execution_id}")
        
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
            logger.info(f"✅ Strategy {execution_id} completed (fallback)")
            
            # Cleanup de la stratégie dans gsgui.ini après exécution complète
            await self._cleanup_completed_strategy(context['challenge_id'], context['profile_id'])
            
        except Exception as e:
            logger.error(f"Strategy execution failed (fallback): {str(e)}")
            context['status'] = 'failed'
        
        finally:
            # Cleanup after delay
            await asyncio.sleep(300)  # Keep for 5 minutes
            if execution_id in self.active_executions:
                del self.active_executions[execution_id]
    
    async def _cleanup_completed_strategy(self, challenge_id: str, profile_id: str):
        """Nettoie une stratégie terminée de gsgui.ini"""
        try:
            logger.info(f"🧹 Cleanup de la stratégie terminée pour challenge {challenge_id} (profil: {profile_id})")
            
            # Importer la fonction de cleanup depuis gs_backend
            import sys
            import os
            # Ajouter le répertoire parent au path pour importer gs_backend
            backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            if backend_dir not in sys.path:
                sys.path.insert(0, backend_dir)
            
            # Importer la fonction de suppression
            from gs_backend import remove_challenge_strategy, log_and_broadcast
            
            # Supprimer la stratégie du fichier gsgui.ini
            success = remove_challenge_strategy(challenge_id, profile_id)
            
            if success:
                cleanup_message = f"🧹 Stratégie extended terminée et nettoyée pour challenge {challenge_id}"
                logger.info(cleanup_message)
                log_and_broadcast(cleanup_message, "cleanup", profile_id)
                
                # Déclencher un refresh du frontend via WebSocket
                await connection_manager.notify_challenge_update(profile_id, {
                    "action": "strategy_cleanup_completed",
                    "challenge_id": challenge_id,
                    "strategy_type": "extended"
                })
                logger.info(f"📡 Frontend refresh déclenché pour challenge {challenge_id}")
            else:
                logger.warning(f"⚠️ Stratégie déjà nettoyée pour challenge {challenge_id}")
                
        except Exception as e:
            logger.error(f"❌ Erreur cleanup stratégie extended: {e}")
    
    async def _execute_action(self, execution_id: str, action: Dict) -> Dict[str, Any]:
        """Execute a single action"""
        context = self.active_executions[execution_id]
        api_client = context['api_client']
        challenge_id = int(context['challenge_id'])
        challenge_url = context['challenge_url']
        profile_id = context['profile_id']
        
        action_type = action['action']
        params = action['parameters']
        
        logger.info(f"🔧 Executing {action_type} with params {params}")
        
        # Get challenge title for better logging
        profile_id = context['profile_id']
        challenge_title = get_challenge_title_from_cache(str(challenge_id))
        challenge_name = challenge_title if challenge_title != str(challenge_id) else f"Challenge {challenge_id}"
        
        # Log action start to frontend
        log_and_broadcast(
            f"🔧 Executing {action_type} action on {challenge_name}...",
            level="info",
            profile_id=profile_id,
            challenge_id=str(challenge_id)
        )
        
        try:
            result = None
            if action_type == 'vote':
                result = await self._execute_vote_action(api_client, challenge_url, params, profile_id, str(challenge_id))
            
            elif action_type == 'submit':
                result = await self._execute_submit_action(api_client, challenge_id, params)
            
            elif action_type == 'swap':
                result = await self._execute_swap_action(api_client, challenge_id, params)
            
            elif action_type == 'boost':
                result = await self._execute_boost_action(api_client, challenge_id, challenge_url, params)
            
            elif action_type == 'turbo':
                result = await self._execute_turbo_action(api_client, challenge_id, challenge_url, params)

            elif action_type == 'unlocked_boost':
                result = await self._execute_unlocked_boost_action(api_client, challenge_id, challenge_url, params, profile_id)
            else:
                result = {'success': False, 'error': f'Unknown action: {action_type}'}
            
            # Déclencher un refresh du frontend pour les actions futures réussies
            profile_id = context['profile_id']
            if result and result.get('success', True):  # True par défaut si pas de champ success
                await connection_manager.notify_challenge_update(profile_id, {
                    "action": f"{action_type}_completed",
                    "challenge_id": str(challenge_id),
                    "strategy_type": "extended",
                    "immediate": False
                })
                logger.info(f"📡 Frontend refresh déclenché pour action future {action_type} sur challenge {challenge_id}")
            
            return result
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _execute_vote_action(self, api_client: GuruShotsAPI, challenge_url: str, params: List[str], profile_id: str = None, challenge_id: str = None) -> Dict:
        """Execute vote action using the same approach as simple_vote()"""
        if not params:
            return {'success': False, 'error': 'Vote count required'}
        
        try:
            vote_count = int(params[0])
            
            # Si pas d'URL fournie, on ne peut pas voter
            if not challenge_url:
                return {
                    'success': False, 
                    'error': 'Challenge URL is required for voting',
                    'vote_count': vote_count,
                    'challenge_url': challenge_url
                }
            
            # Utiliser le challenge_id passé en paramètre
            if challenge_id:
                challenge_name = get_challenge_title_from_cache(str(challenge_id))
            else:
                challenge_name = "Unknown Challenge"
            
            # Log avant l'action avec WebSocket
            log_and_broadcast(f"🗳️ Executing vote: {vote_count} votes on {challenge_name}", "info", profile_id)
            logger.info(f"🗳️ Executing vote: {vote_count} votes on {challenge_url}")
            
            # Utiliser exactement la même méthode que simple_vote() qui fonctionne
            vote_result = await api_client.execute_simple_vote(challenge_url, vote_count)
            
            # Convert VoteResult object to dictionary format (comme avant)
            result = {
                'success': vote_result.success,
                'message': vote_result.message,
                'vote_count': vote_count,
                'challenge_url': challenge_url,
                'result_data': getattr(vote_result, 'result_data', None)
            }
            
            # Log du résultat avec WebSocket
            if result['success']:
                log_and_broadcast(f"✅ Vote successful: {vote_count} votes cast on {challenge_name} - {result['message']}", "success", profile_id)
                logger.info(f"✅ Vote successful: {vote_count} votes cast - {result['message']}")
            else:
                log_and_broadcast(f"❌ Vote failed on {challenge_name}: {result['message']}", "error", profile_id)
                logger.error(f"❌ Vote failed: {result['message']}")
                
            return result
            
        except ValueError:
            return {'success': False, 'error': 'Invalid vote count'}
        except Exception as e:
            logger.error(f"❌ Vote execution error: {str(e)}")
            return {
                'success': False, 
                'error': f'Vote execution error: {str(e)}',
                'vote_count': vote_count if 'vote_count' in locals() else 0,
                'challenge_url': challenge_url
            }
    
    async def _execute_submit_action(self, api_client: GuruShotsAPI, challenge_id: int, params: List[str]) -> Dict:
        """Execute submit action - submit multiple photos with IDs passed as hard parameters"""
        try:
            if not params:
                return {'success': False, 'error': 'Image ID(s) required for submit'}
            
            # All parameters are photo IDs to submit (no index resolution needed)
            image_ids = [param.strip() for param in params if param.strip()]
            
            if not image_ids:
                return {'success': False, 'error': 'No valid image IDs provided'}
            
            logger.info(f"📸 Submitting {len(image_ids)} photos to challenge {challenge_id}: {image_ids}")
            
            # Use submit_photo method with ALL IDs at once (creates image_ids[0], image_ids[1], etc.)
            result = await api_client.submit_photo(challenge_id, image_ids)
            
            if result.get('success', True):  # Assume success if not explicitly failed
                logger.info(f"✅ Successfully submitted {len(image_ids)} photos to challenge {challenge_id}")
                return {
                    'success': True,
                    'message': f'Submitted {len(image_ids)} photos to challenge {challenge_id}',
                    'challenge_id': challenge_id,
                    'image_ids': image_ids,
                    'submission_count': len(image_ids)
                }
            else:
                error_msg = result.get('error', 'Submission failed')
                logger.error(f"❌ Submit failed: {error_msg}")
                return {'success': False, 'error': error_msg}
                
        except Exception as e:
            logger.error(f"❌ Exception during submit: {str(e)}")
            return {'success': False, 'error': str(e)}
    
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
        """Execute boost action - same logic as turbo with FRESH photo list and index resolution"""
        try:
            logger.info(f"🚀 Starting boost action for challenge {challenge_id}")
            
            if not params:
                return {'success': False, 'error': 'Image ID or index required for boost'}
            
            # Check if a photo index is specified for targeting
            target_photo_id = None
            param = params[0].strip()
            
            # Handle index notation
            if param.startswith('[') and param.endswith(']'):
                index_str = param[1:-1]
            else:
                index_str = param
            
            if index_str.isdigit():
                index = int(index_str)
                logger.info(f"🎯 Resolving photo index [{index}] by fetching FRESH challenge data for boost")
                
                # GET FRESH CHALLENGE DATA at execution time (same as turbo)
                target_photo_id = await self._get_current_user_photo_by_index(api_client, challenge_id, index)
                if target_photo_id:
                    logger.info(f"✅ Boost will target photo {target_photo_id} (index [{index}] from fresh data)")
                else:
                    logger.error(f"❌ Could not resolve photo index [{index}] from current challenge data")
                    return {'success': False, 'error': f'Could not resolve photo index {index}'}
            else:
                target_photo_id = param
                logger.info(f"🎯 Boost will target specific photo: {target_photo_id}")
            
            if not target_photo_id:
                logger.error("❌ No target photo specified for boost action")
                return {'success': False, 'error': 'No target photo specified'}
            
            # Use boost_photo method
            logger.info(f"⚡ Calling boost_photo(challenge_id={challenge_id}, photo_id={target_photo_id})")
            result = await api_client.boost_photo(challenge_id, target_photo_id)
            
            if result.get('success', True):
                logger.info(f"⚡ Successfully boosted photo {target_photo_id} in challenge {challenge_id}")
                return {
                    'success': True,
                    'message': f'Boosted photo {target_photo_id}',
                    'challenge_id': challenge_id,
                    'target_photo_id': target_photo_id,
                    'resolved_from_index': index_str if index_str.isdigit() else None
                }
            else:
                error_msg = result.get('error', 'Boost failed')
                logger.error(f"❌ Boost failed: {error_msg}")
                return {'success': False, 'error': error_msg}
                
        except Exception as e:
            logger.error(f"❌ Exception during boost: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def _execute_turbo_action(self, api_client: GuruShotsAPI, challenge_id: int, challenge_url: str, params: List[str]) -> Dict:
        """Execute turbo action - fetch FRESH photo list at execution time for accurate targeting"""
        try:
            logger.info(f"🚀 Starting turbo action for challenge {challenge_id}")
            
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
                    logger.info(f"🎯 Resolving photo index [{index}] by fetching FRESH challenge data")
                    
                    # GET FRESH CHALLENGE DATA at execution time
                    target_photo_id = await self._get_current_user_photo_by_index(api_client, challenge_id, index)
                    if target_photo_id:
                        logger.info(f"✅ Turbo will target photo {target_photo_id} (index [{index}] from fresh data)")
                    else:
                        logger.error(f"❌ Could not resolve photo index [{index}] from current challenge data")
                        return {'success': False, 'error': f'Could not resolve photo index {index}'}
                else:
                    target_photo_id = param
                    logger.info(f"🎯 Turbo will target specific photo: {target_photo_id}")
            
            if not target_photo_id:
                logger.error("❌ No target photo specified for turbo action")
                return {'success': False, 'error': 'No target photo specified'}
            
            # Use set_turbo method (unlock turbo)
            logger.info(f"🚀 Calling set_turbo(challenge_id={challenge_id}, photo_id={target_photo_id})")
            result = await api_client.set_turbo(challenge_id, target_photo_id)
            
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

    async def _execute_unlocked_boost_action(self, api_client: GuruShotsAPI, challenge_id: int, challenge_url: str,
                                    params: List[str], profile_id: str) -> Dict:
        """Execute unlocked action - fetch FRESH photo list at execution time for accurate targeting"""
        try:
            logger.info(f"🚀 Starting unlocked action for challenge {challenge_id}")

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
                    logger.info(f"🎯 Resolving photo index [{index}] by fetching FRESH challenge data")

                    # GET FRESH CHALLENGE DATA at execution time
                    target_photo_id = await self._get_current_user_photo_by_index(api_client, challenge_id, index)
                    if target_photo_id:
                        logger.info(f"✅ Turbo will target photo {target_photo_id} (index [{index}] from fresh data)")
                    else:
                        logger.error(f"❌ Could not resolve photo index [{index}] from current challenge data")
                        return {'success': False, 'error': f'Could not resolve photo index {index}'}
                else:
                    target_photo_id = param
                    logger.info(f"🎯 Turbo will target specific photo: {target_photo_id}")

            if not target_photo_id:
                logger.error("❌ No target photo specified for turbo action")
                return {'success': False, 'error': 'No target photo specified'}

            # Use set_turbo method (unlock turbo)
            logger.info(f"🚀 Calling set_turbo(challenge_id={challenge_id}, photo_id={target_photo_id})")

            available = await self._get_challenge_boost_unlocked(api_client, challenge_id)
            if available == True:
                result = await self._execute_boost_action(api_client, challenge_id, challenge_url,params)
                if result.get('success', True):
                    logger.info(f"🚀 Successfully unlocked turbo for challenge {challenge_id}")
                    vote_result = await api_client.execute_simple_vote(challenge_url, 100)
                    if vote_result.get('success', True):
                        return {
                            'success': True,
                            'message': f'Unlocked turbo for challenge {challenge_id} boosted and vote',
                            'challenge_id': challenge_id,
                            'target_photo_id': target_photo_id,
                            'note': 'Turbo unlocked - specific photo targeting may require additional implementation'
                        }
                    else:
                        error_msg = result.get('error', 'Turbo unlock failed')
                        logger.error(f"❌ Boost, votes failed: {error_msg}")
                        return {'success': False, 'error': error_msg}
                else:
                    error_msg = result.get('error', 'Turbo unlock failed')
                    logger.error(f"❌ Turbo unlock failed: {error_msg}")
                    return {'success': False, 'error': error_msg}
            else:
                #reschedule nest-15m
                execution_id = await self.execute_extended_strategy(profile_id, str(challenge_id), str(challenge_url), 'unlocked_boost')
                return {
                    "success": True,
                    "execution_id": execution_id,
                    "message": f"Started extended strategy unlocked_boost"
                }

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

    async def _get_current_user_info(self, api_client: GuruShotsAPI) -> Optional[Dict[str, Any]]:
        """Get current user information to identify them in rankings"""
        try:
            # Method 1: Try to get user info directly from API
            try:
                user_info = await api_client.get_current_user_info()
                if user_info and user_info.get('user_id'):
                    return {
                        'username': user_info.get('username', ''),
                        'user_id': user_info.get('user_id'),
                        'name': user_info.get('name', '')
                    }
            except Exception as e:
                logger.debug(f"Direct user info method failed: {e}")
            
            # Method 2: Try to get user info from challenges page
            try:
                challenges_response = await api_client.get_challenges()
                
                # Look for user info in challenges response
                if challenges_response and 'user' in challenges_response:
                    user_info = challenges_response['user']
                    return {
                        'username': user_info.get('username', ''),
                        'user_id': user_info.get('id'),
                        'name': user_info.get('name', '')
                    }
                
                # Method 3: Try to get user profile via a challenge detail call
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
            except Exception as e:
                logger.debug(f"Challenges-based user info method failed: {e}")
            
            # All methods failed
            logger.warning("Could not determine current user info from any available methods")
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
    
    async def _resolve_photo_by_index_with_url(self, api_client: GuruShotsAPI, challenge_id: int, challenge_url: str, index: int) -> Optional[str]:
        """Resolve photo ID by index using challenge_url to get challenge details"""
        try:
            logger.info(f"🔍 Using challenge URL {challenge_url} to resolve photo index {index}")
            
            # Get challenge details using the URL
            challenge_details = await api_client.get_challenge_details(challenge_url)
            if not challenge_details.get('challenge'):
                logger.error(f"Could not get challenge details from URL: {challenge_url}")
                return None
            
            # Get current user info to identify them
            current_user_info = await self._get_current_user_info(api_client)
            if not current_user_info:
                logger.error("Could not identify current user")
                return None
            
            current_username = current_user_info.get('username', '').lower()
            current_user_id = current_user_info.get('user_id')
            
            logger.info(f"Resolving photo index {index} for user {current_username} using URL method")
            
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
            
            logger.info(f"✅ Resolved index [{index}] -> photo {photo_id} with {photo_votes} votes (using URL method)")
            
            return photo_id
            
        except Exception as e:
            logger.error(f"Error resolving photo index {index} with URL: {e}")
            return None
    
    async def _get_current_user_photo_by_index(self, api_client: GuruShotsAPI, challenge_id: int, index: int) -> Optional[str]:
        """Get current user's photo ID by index using direct get_my_active_challenges API call - FRESH DATA"""
        try:
            import aiohttp
            
            logger.info(f"🔍 Calling get_my_active_challenges API directly to resolve photo index {index} for challenge {challenge_id}")
            
            # Direct API call to get_my_active_challenges (like frontend does)
            async with aiohttp.ClientSession(
                headers=api_client.headers,
                connector=aiohttp.TCPConnector(ssl=False)
            ) as session:
                async with session.post(f'{api_client.base_url}/get_my_active_challenges') as response:
                    if response.status != 200:
                        logger.error(f"❌ API Error: Status {response.status}")
                        return None
                    
                    data = await response.json()
                    logger.info(f"📊 API Response received, looking for challenge {challenge_id}")
                    
                    # Find the specific challenge in the response
                    target_challenge = None
                    for challenge_data in data.get('challenges', []):
                        if str(challenge_data.get('id')) == str(challenge_id):
                            target_challenge = challenge_data
                            logger.info(f"✅ Found challenge {challenge_id}: {challenge_data.get('title', 'No title')}")
                            break
                    
                    if not target_challenge:
                        logger.error(f"❌ Challenge {challenge_id} not found in active challenges")
                        return None
                    
                    # Get user's entries directly from the API response
                    user_entries = target_challenge.get('member', []).get('ranking', []).get('entries', [])
                    
                    if not user_entries:
                        logger.error(f"❌ No user entries found in challenge {challenge_id}")
                        return None
                    
                    # Sort entries by votes (descending: most votes first) 
                    #sorted_entries = sorted(user_entries, key=lambda x: x.get('votes', 0), reverse=True)
                    
                    # Check if index is valid
                    #if index < 0 or index >= len(sorted_entries):
                    #    logger.error(f"❌ Photo index {index} out of range (user has {len(sorted_entries)} photos)")
                    #    return None
                    
                    # Get photo ID at requested index
                    selected_photo = user_entries[index]
                    photo_id = selected_photo['id']
                    photo_votes = selected_photo.get('votes', 0)
                    
                    logger.info(f"✅ Resolved index [{index}] -> photo {photo_id} with {photo_votes} votes (DIRECT API CALL)")
                    
                    return photo_id
            
        except Exception as e:
            logger.error(f"❌ Error calling get_my_active_challenges API for index {index}: {e}")
            return None
    
    async def _get_challenge_end_time(self, api_client: GuruShotsAPI, challenge_id: str) -> datetime:
        """Get challenge end time using direct get_my_active_challenges API call"""
        try:
            import aiohttp
            
            logger.info(f"🔍 Getting challenge end time for challenge {challenge_id} via direct API call")
            
            # Direct API call to get_my_active_challenges (like frontend does)
            async with aiohttp.ClientSession(
                headers=api_client.headers,
                connector=aiohttp.TCPConnector(ssl=False)
            ) as session:
                async with session.post(f'{api_client.base_url}/get_my_active_challenges') as response:
                    if response.status != 200:
                        logger.error(f"❌ API Error: Status {response.status}")
                        return datetime.now() + timedelta(hours=24)
                    
                    data = await response.json()
                    
                    # Find the specific challenge we're looking for
                    for challenge_data in data.get('challenges', []):
                        if str(challenge_data.get('id')) == str(challenge_id):
                            # Get end_time from the challenge data
                            close_time = challenge_data.get('close_time')
                            if close_time:
                                challenge_end_time = datetime.fromtimestamp(close_time)
                                logger.info(f"✅ Found challenge {challenge_id} end time: {challenge_end_time}")
                                return challenge_end_time
                    
                    # If not found, fallback to a reasonable default (24 hours from now)
                    logger.warning(f"⚠️ Challenge {challenge_id} not found in active challenges, using 24h fallback")
                    return datetime.now() + timedelta(hours=24)
            
        except Exception as e:
            logger.error(f"❌ Error getting challenge end time via API: {e}")
            # Fallback to 24 hours from now if we can't get the real end time
            return datetime.now() + timedelta(hours=24)

    async def _get_challenge_boost_unlocked(self, api_client: GuruShotsAPI, challenge_id: int) -> boolean:
        """Get challenge end time using direct get_my_active_challenges API call"""
        try:
            import aiohttp

            logger.info(f"🔍 Getting challenge end time for challenge {challenge_id} via direct API call")

            # Direct API call to get_my_active_challenges (like frontend does)
            async with aiohttp.ClientSession(
                    headers=api_client.headers,
                    connector=aiohttp.TCPConnector(ssl=False)
            ) as session:
                async with session.post(f'{api_client.base_url}/get_my_active_challenges') as response:
                    if response.status != 200:
                        logger.error(f"❌ API Error: Status {response.status}")
                        return False

                    data = await response.json()

                    # Find the specific challenge we're looking for
                    for challenge_data in data.get('challenges', []):
                        if str(challenge_data.get('id')) == str(challenge_id):
                            # Get end_time from the challenge data
                            # not MISSED

                            boosted = challenge_data['member']['boost']['state']

                            if boosted == 'AVAILABLE' and await self._is_challenge_ending_soon(challenge_data['member']['boost']['timeout'], 1.0): # and  challenge_data['member']['boost']['timeout'] < '1H':
                                logger.info(f"✅ Boost Unlocked For challenge {challenge_id} ")
                                return True
                            else:
                                logger.info(f"✅ Boost Available but too soon For challenge {challenge_id} ")
                                return False
                    # If not found, fallback to a reasonable default (24 hours from now)
                    logger.warning(f"⚠️ Challenge {challenge_id} not found in active challenges, using 24h fallback")
                    return False

        except Exception as e:
            logger.error(f"❌ Error getting challenge end time via API: {e}")
            # Fallback to 24 hours from now if we can't get the real end time
            return False

    async def _is_challenge_ending_soon(self, timeout_timestamp: int, threshold_hours: float = 1.0) -> bool:
        """
        Check if a challenge is ending within the specified threshold

        Args:
            timeout_timestamp: Unix timestamp indicating when the challenge ends
            threshold_hours: Hours before end to consider "ending soon" (default: 1.0)

        Returns:
            True if challenge ends within threshold_hours, False otherwise
        """
        try:
            # Convert timestamp to datetime
            challenge_end = datetime.fromtimestamp(timeout_timestamp)
            now = datetime.now()

            # Calculate time remaining
            time_remaining = challenge_end - now
            remaining_hours = time_remaining.total_seconds() / 3600

            logger.debug(f"Challenge ends at {challenge_end}, remaining: {remaining_hours:.2f}h")

            return remaining_hours < threshold_hours and remaining_hours > 0

        except (ValueError, OSError, OverflowError) as e:
            logger.error(f"Invalid timestamp {timeout_timestamp}: {e}")
            return False

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
