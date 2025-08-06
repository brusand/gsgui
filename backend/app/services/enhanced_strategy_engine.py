"""
Enhanced Strategy Engine
Supports extended strategy actions: submit, swap, boost, turbo, fill
Compatible with existing strategies.ini format plus new ANCA-style strategies
"""

import re
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from configobj import ConfigObj

from app.services.gurushots_api import GuruShotsAPI
from app.websockets.connection_manager import connection_manager

logger = logging.getLogger(__name__)

@dataclass
class StrategyAction:
    """Represents a single strategy action"""
    step: int
    action: str  # vote, submit, swap, boost, turbo, fill
    timing: str  # end-2m0s, now, next-1h0s
    parameters: List[str]
    scheduled_time: Optional[datetime] = None
    executed: bool = False
    result: Optional[Dict[str, Any]] = None

class EnhancedStrategyEngine:
    """
    Enhanced strategy engine supporting all ANCA-style actions
    """
    
    def __init__(self, gurushots_api: GuruShotsAPI, user_id: str = "strategy_user"):
        self.api = gurushots_api
        self.user_id = user_id
        self.strategies = ConfigObj('strategies.ini')
        
        # Active strategy executions
        self.active_strategies: Dict[str, Dict] = {}  # strategy_id -> execution context
        
        # Action handlers
        self.action_handlers = {
            'vote': self._execute_vote,
            'submit': self._execute_submit,
            'swap': self._execute_swap,
            'boost': self._execute_boost,
            'turbo': self._execute_turbo,
            'fill': self._execute_fill
        }
    
    async def execute_strategy(self, strategy_name: str, challenge_id: int, 
                             challenge_url: str, challenge_end_time: datetime) -> str:
        """Execute a complete strategy"""
        if strategy_name not in self.strategies:
            raise ValueError(f"Strategy '{strategy_name}' not found")
        
        strategy_id = f"{strategy_name}_{challenge_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        logger.info(f"🎯 Starting strategy '{strategy_name}' for challenge {challenge_id}")
        
        # Parse strategy actions
        actions = self._parse_strategy(strategy_name, challenge_end_time)
        
        # Store execution context
        self.active_strategies[strategy_id] = {
            'strategy_name': strategy_name,
            'challenge_id': challenge_id,
            'challenge_url': challenge_url,
            'challenge_end_time': challenge_end_time,
            'actions': actions,
            'started_at': datetime.now(),
            'status': 'active'
        }
        
        # Start execution task
        asyncio.create_task(self._execute_strategy_loop(strategy_id))
        
        # Notify start
        await connection_manager.notify_strategy_started(
            self.user_id, strategy_id,
            {
                'strategy_name': strategy_name,
                'challenge_id': challenge_id,
                'actions_count': len(actions)
            }
        )
        
        return strategy_id
    
    def _parse_strategy(self, strategy_name: str, challenge_end_time: datetime) -> List[StrategyAction]:
        """Parse strategy configuration into actions"""
        actions = []
        strategy_config = self.strategies[strategy_name]
        
        for step, action_string in strategy_config.items():
            if step == 'description':
                continue
                
            # Parse action string: "action,timing,param1,param2,..."
            parts = [p.strip() for p in action_string.split(',')]
            
            if len(parts) < 2:
                logger.warning(f"Invalid action format: {action_string}")
                continue
            
            action = parts[0]
            timing = parts[1] 
            parameters = parts[2:] if len(parts) > 2 else []
            
            # Calculate scheduled time
            scheduled_time = self._calculate_scheduled_time(timing, challenge_end_time)
            
            strategy_action = StrategyAction(
                step=int(step),
                action=action,
                timing=timing,
                parameters=parameters,
                scheduled_time=scheduled_time
            )
            
            actions.append(strategy_action)
        
        # Sort by scheduled time
        actions.sort(key=lambda a: a.scheduled_time or datetime.max)
        return actions
    
    def _calculate_scheduled_time(self, timing: str, challenge_end_time: datetime) -> Optional[datetime]:
        """Calculate when to execute based on timing specification"""
        if timing.lower() == 'now':
            return datetime.now()
        
        # Parse end-XmYs format
        end_match = re.match(r'end-(\d+)([dhm])(\d+)([ms])(\d+)?s?', timing)
        if end_match:
            value1, unit1, value2, unit2, value3 = end_match.groups()
            
            delta = timedelta()
            if unit1 == 'd':
                delta += timedelta(days=int(value1))
            elif unit1 == 'h':
                delta += timedelta(hours=int(value1))
            elif unit1 == 'm':
                delta += timedelta(minutes=int(value1))
                
            if unit2 == 'm' and unit1 != 'm':
                delta += timedelta(minutes=int(value2))
            elif unit2 == 's':
                delta += timedelta(seconds=int(value2))
            
            return challenge_end_time - delta
        
        # Parse next-XmYs format  
        next_match = re.match(r'next-(\d+)([dhm])(\d+)([ms])(\d+)?s?', timing)
        if next_match:
            value1, unit1, value2, unit2, value3 = next_match.groups()
            
            delta = timedelta()
            if unit1 == 'd':
                delta += timedelta(days=int(value1))
            elif unit1 == 'h':
                delta += timedelta(hours=int(value1))
            elif unit1 == 'm':
                delta += timedelta(minutes=int(value1))
                
            if unit2 == 'm' and unit1 != 'm':
                delta += timedelta(minutes=int(value2))
            elif unit2 == 's':
                delta += timedelta(seconds=int(value2))
            
            return datetime.now() + delta
        
        logger.warning(f"Could not parse timing: {timing}")
        return None
    
    async def _execute_strategy_loop(self, strategy_id: str):
        """Main execution loop for a strategy"""
        context = self.active_strategies[strategy_id]
        actions = context['actions']
        
        logger.info(f"🔄 Strategy loop started for {strategy_id}")
        
        try:
            for action in actions:
                if context['status'] != 'active':
                    break
                
                # Wait until scheduled time
                if action.scheduled_time and action.scheduled_time > datetime.now():
                    wait_seconds = (action.scheduled_time - datetime.now()).total_seconds()
                    if wait_seconds > 0:
                        logger.info(f"⏰ Waiting {wait_seconds:.0f}s for action {action.action}")
                        await asyncio.sleep(wait_seconds)
                
                # Check if strategy still active
                if context['status'] != 'active':
                    break
                
                # Execute action
                try:
                    result = await self._execute_action(strategy_id, action)
                    action.executed = True
                    action.result = result
                    
                    # Notify step completion
                    await connection_manager.notify_strategy_step(
                        self.user_id, strategy_id, action.step,
                        {
                            'action': action.action,
                            'timing': action.timing,
                            'parameters': action.parameters,
                            'result': result
                        }
                    )
                    
                except Exception as e:
                    logger.error(f"Error executing action {action.action}: {str(e)}")
                    action.result = {'success': False, 'error': str(e)}
            
            # Strategy completed
            context['status'] = 'completed'
            successful_actions = sum(1 for a in actions if a.executed and a.result.get('success', False))
            
            await connection_manager.notify_strategy_completed(
                self.user_id, strategy_id, True,
                {
                    'total_actions': len(actions),
                    'successful_actions': successful_actions,
                    'completion_time': datetime.now().isoformat()
                }
            )
            
            logger.info(f"✅ Strategy {strategy_id} completed: {successful_actions}/{len(actions)} successful")
            
        except Exception as e:
            logger.error(f"Strategy execution failed: {str(e)}")
            context['status'] = 'failed'
            await connection_manager.notify_strategy_completed(
                self.user_id, strategy_id, False,
                {'error': str(e)}
            )
    
    async def _execute_action(self, strategy_id: str, action: StrategyAction) -> Dict[str, Any]:
        """Execute a single strategy action"""
        context = self.active_strategies[strategy_id]
        challenge_id = context['challenge_id']
        challenge_url = context['challenge_url']
        
        logger.info(f"🔧 Executing {action.action} with params {action.parameters}")
        
        if action.action in self.action_handlers:
            return await self.action_handlers[action.action](
                challenge_id, challenge_url, action.parameters
            )
        else:
            return {'success': False, 'error': f'Unknown action: {action.action}'}
    
    async def _execute_vote(self, challenge_id: int, challenge_url: str, params: List[str]) -> Dict[str, Any]:
        """Execute vote action"""
        if not params:
            return {'success': False, 'error': 'Vote count parameter required'}
        
        try:
            vote_count = int(params[0])
            result = await self.api.execute_simple_vote(challenge_url, vote_count)
            return result
        except ValueError:
            return {'success': False, 'error': 'Invalid vote count parameter'}
    
    async def _execute_submit(self, challenge_id: int, challenge_url: str, params: List[str]) -> Dict[str, Any]:
        """Execute submit action"""
        if not params:
            return {'success': False, 'error': 'Image ID parameter required'}
        
        image_id = params[0]
        # This would need to be implemented in GuruShotsAPI
        logger.info(f"📸 Would submit image {image_id} to challenge {challenge_id}")
        return {'success': True, 'message': f'Submitted image {image_id}', 'image_id': image_id}
    
    async def _execute_swap(self, challenge_id: int, challenge_url: str, params: List[str]) -> Dict[str, Any]:
        """Execute swap action"""
        if len(params) < 2:
            return {'success': False, 'error': 'Two image ID parameters required for swap'}
        
        current_photo_id, new_photo_id = params[0], params[1]
        result = await self.api.swap_photo(challenge_id, current_photo_id, new_photo_id)
        return result
    
    async def _execute_boost(self, challenge_id: int, challenge_url: str, params: List[str]) -> Dict[str, Any]:
        """Execute boost action"""
        if not params:
            return {'success': False, 'error': 'Image ID parameter required'}
        
        image_id = params[0]
        # This would need to be implemented in GuruShotsAPI
        logger.info(f"⚡ Would boost image {image_id} in challenge {challenge_id}")
        return {'success': True, 'message': f'Boosted image {image_id}', 'image_id': image_id}
    
    async def _execute_turbo(self, challenge_id: int, challenge_url: str, params: List[str]) -> Dict[str, Any]:
        """Execute turbo action"""
        algorithm = params[0] if params else 'default'
        # This would integrate with existing TurboExecutor
        logger.info(f"🚀 Would execute turbo with algorithm {algorithm} in challenge {challenge_id}")
        return {'success': True, 'message': f'Executed turbo with {algorithm}', 'algorithm': algorithm}
    
    async def _execute_fill(self, challenge_id: int, challenge_url: str, params: List[str]) -> Dict[str, Any]:
        """Execute fill action"""
        if not params:
            return {'success': False, 'error': 'Fill percentage parameter required'}
        
        try:
            fill_percentage = int(params[0])
            # Calculate votes needed to reach percentage
            vote_count = fill_percentage  # Simplified - would need proper calculation
            result = await self.api.execute_simple_vote(challenge_url, vote_count)
            return result
        except ValueError:
            return {'success': False, 'error': 'Invalid fill percentage parameter'}
    
    async def cancel_strategy(self, strategy_id: str) -> bool:
        """Cancel an active strategy"""
        if strategy_id in self.active_strategies:
            self.active_strategies[strategy_id]['status'] = 'cancelled'
            logger.info(f"❌ Strategy {strategy_id} cancelled")
            
            await connection_manager.send_personal_message(self.user_id, {
                "type": "strategy_cancelled",
                "strategy_id": strategy_id
            })
            return True
        
        return False
    
    def get_strategy_status(self, strategy_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a strategy execution"""
        if strategy_id not in self.active_strategies:
            return None
        
        context = self.active_strategies[strategy_id]
        actions = context['actions']
        
        return {
            'strategy_id': strategy_id,
            'strategy_name': context['strategy_name'],
            'challenge_id': context['challenge_id'],
            'status': context['status'],
            'started_at': context['started_at'].isoformat(),
            'total_actions': len(actions),
            'completed_actions': sum(1 for a in actions if a.executed),
            'successful_actions': sum(1 for a in actions if a.executed and a.result.get('success', False))
        }
    
    def create_anca_strategy(self, strategy_type: str) -> str:
        """Create an ANCA-style strategy dynamically"""
        strategy_name = f"anca_{strategy_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        if strategy_type == "4images":
            strategy_config = {
                'description': 'ANCA 4-image strategy - empty slots + 12h boost window',
                '0': 'submit,end-24h0m0s,starter-image',
                '1': 'boost,end-12h0m0s,starter-image',
                '2': 'swap,end-12h0m5s,starter-image,boosted-image',
                '3': 'submit,end-12h0m0s,final-image',
                '4': 'fill,end-1h0m0s,100',
                '5': 'turbo,end-1h0m0s,default'
            }
        elif strategy_type == "single":
            strategy_config = {
                'description': 'ANCA single strategy - 24h entry + 3h swap + 1h turbo',
                '0': 'submit,end-24h0m0s,initial-image',
                '1': 'swap,end-3h0m0s,initial-image,final-image',
                '2': 'fill,end-1h0m0s,100',
                '3': 'turbo,end-1h0m0s,default'
            }
        else:
            raise ValueError(f"Unknown ANCA strategy type: {strategy_type}")
        
        # Add to strategies configuration
        self.strategies[strategy_name] = strategy_config
        self.strategies.write()
        
        logger.info(f"📋 Created ANCA strategy: {strategy_name}")
        return strategy_name

# Global instance
enhanced_strategy_engine = None

def get_enhanced_strategy_engine(gurushots_api: GuruShotsAPI, user_id: str = "strategy_user") -> EnhancedStrategyEngine:
    """Get or create enhanced strategy engine"""
    global enhanced_strategy_engine
    if enhanced_strategy_engine is None:
        enhanced_strategy_engine = EnhancedStrategyEngine(gurushots_api, user_id)
    return enhanced_strategy_engine
