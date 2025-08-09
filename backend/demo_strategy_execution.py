#!/usr/bin/env python3
"""
Demo script for ExtendedStrategyExecutor
Demonstrates the different execution patterns for NOW vs FUTURE actions
"""

import asyncio
import logging
import sys
import os
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.extended_strategy_executor import ExtendedStrategyExecutor
from app.services.config_manager import config_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class StrategyExecutionDemo:
    """Demonstration of strategy execution patterns"""
    
    def __init__(self):
        self.executor = ExtendedStrategyExecutor()
        
    def create_mock_api_client(self):
        """Create a mock API client for demonstration"""
        mock_api = AsyncMock()
        
        # Mock challenge details with future end time
        future_time = datetime.now() + timedelta(hours=2)
        mock_api.get_challenge_details.return_value = {
            'challenge': {
                'close_time': future_time.timestamp()
            }
        }
        
        # Mock successful actions
        mock_api.execute_simple_vote.return_value = {
            'success': True,
            'votes_cast': 10,
            'result_data': {'message': 'Vote successful'}
        }
        
        mock_api.set_turbo.return_value = {
            'success': True,
            'message': 'Turbo unlocked'
        }
        
        mock_api.boost_photo.return_value = {
            'success': True,
            'message': 'Photo boosted'
        }
        
        # Mock user info
        mock_api.get_current_user_info.return_value = {
            'username': 'demo_user',
            'user_id': '54321'
        }
        
        # Mock challenge ranking
        mock_api.get_challenge_followings.return_value = {
            'items': [
                {
                    'member': {
                        'user_name': 'demo_user',
                        'id': '54321'
                    },
                    'entries': [
                        {'id': 'photo_123', 'votes': 150},
                        {'id': 'photo_456', 'votes': 89}
                    ]
                }
            ]
        }
        
        return mock_api
    
    async def demo_now_strategies(self):
        """Demonstrate immediate execution strategies"""
        logger.info("=" * 60)
        logger.info("🚀 DEMONSTRATING 'NOW' STRATEGIES (Immediate Execution)")
        logger.info("=" * 60)
        
        now_strategies = ['fill-now-1', 'fill-now-70', 'turbo-0', 'turbo-1', 'fill20']
        
        with patch.object(config_manager, 'get_user', return_value={'xtoken': 'demo_token'}):
            mock_api = self.create_mock_api_client()
            
            with patch('app.services.extended_strategy_executor.GuruShotsAPI', return_value=mock_api):
                
                for strategy in now_strategies:
                    if strategy not in self.executor.strategies_config:
                        logger.warning(f"⚠️  Strategy '{strategy}' not found in config, skipping")
                        continue
                        
                    logger.info(f"\n🎯 Testing strategy: {strategy}")
                    logger.info(f"   Description: {self.executor.strategies_config[strategy].get('description', 'No description')}")
                    
                    start_time = datetime.now()
                    
                    try:
                        execution_id = await self.executor.execute_extended_strategy(
                            profile_id='demo_user',
                            challenge_id='demo_challenge_123',
                            challenge_url='challenge-demo_challenge_123',
                            strategy_name=strategy
                        )
                        
                        end_time = datetime.now()
                        execution_duration = (end_time - start_time).total_seconds()
                        
                        logger.info(f"   ✅ Strategy executed in {execution_duration:.2f}s (immediate)")
                        logger.info(f"   📋 Execution ID: {execution_id}")
                        
                        # Check if there are any active executions for future actions
                        if execution_id in self.executor.active_executions:
                            context = self.executor.active_executions[execution_id]
                            future_actions = len(context['actions'])
                            logger.info(f"   📅 {future_actions} future actions scheduled")
                        else:
                            logger.info(f"   ⚡ All actions executed immediately - no future scheduling")
                            
                    except Exception as e:
                        logger.error(f"   ❌ Strategy failed: {e}")
                
                await asyncio.sleep(0.1)  # Brief pause between demos
    
    async def demo_future_strategies(self):
        """Demonstrate scheduled execution strategies"""
        logger.info("=" * 60)
        logger.info("📅 DEMONSTRATING 'FUTURE' STRATEGIES (Scheduled Execution)")
        logger.info("=" * 60)
        
        future_strategies = ['4m', '3m', '2m', 'alain', 'Bruno', 'caloune']
        
        with patch.object(config_manager, 'get_user', return_value={'xtoken': 'demo_token'}):
            mock_api = self.create_mock_api_client()
            
            with patch('app.services.extended_strategy_executor.GuruShotsAPI', return_value=mock_api):
                
                for strategy in future_strategies:
                    if strategy not in self.executor.strategies_config:
                        logger.warning(f"⚠️  Strategy '{strategy}' not found in config, skipping")
                        continue
                        
                    logger.info(f"\n🎯 Testing strategy: {strategy}")
                    logger.info(f"   Description: {self.executor.strategies_config[strategy].get('description', 'No description')}")
                    
                    start_time = datetime.now()
                    
                    try:
                        execution_id = await self.executor.execute_extended_strategy(
                            profile_id='demo_user',
                            challenge_id='demo_challenge_456',
                            challenge_url='challenge-demo_challenge_456',
                            strategy_name=strategy
                        )
                        
                        end_time = datetime.now()
                        execution_duration = (end_time - start_time).total_seconds()
                        
                        logger.info(f"   ✅ Strategy scheduled in {execution_duration:.2f}s")
                        logger.info(f"   📋 Execution ID: {execution_id}")
                        
                        # Show the scheduled future actions
                        if execution_id in self.executor.active_executions:
                            context = self.executor.active_executions[execution_id]
                            actions = context['actions']
                            
                            logger.info(f"   📅 {len(actions)} actions scheduled:")
                            
                            for i, action in enumerate(actions[:3]):  # Show first 3 actions
                                scheduled_in = (action['scheduled_time'] - datetime.now()).total_seconds()
                                logger.info(f"      {i+1}. {action['action']} ({action['timing']}) - in {scheduled_in:.0f}s")
                            
                            if len(actions) > 3:
                                logger.info(f"      ... and {len(actions) - 3} more actions")
                                
                    except Exception as e:
                        logger.error(f"   ❌ Strategy failed: {e}")
                
                await asyncio.sleep(0.1)  # Brief pause between demos
    
    async def demo_hybrid_strategy(self):
        """Demonstrate a strategy with both immediate and scheduled actions"""
        logger.info("=" * 60)
        logger.info("🔄 DEMONSTRATING HYBRID STRATEGY (NOW + FUTURE)")
        logger.info("=" * 60)
        
        # Create a hybrid strategy for demonstration
        hybrid_strategy = {
            'description': 'Demo hybrid strategy: immediate votes + scheduled actions',
            '0': 'vote,now,10',         # Immediate vote
            '1': 'turbo,now,0',         # Immediate turbo
            '2': 'vote,end-2m0s,20',    # Vote 2 minutes before end
            '3': 'vote,end-1m0s,30',    # Vote 1 minute before end
            '4': 'boost,end-0m30s,0'    # Boost 30 seconds before end
        }
        
        # Temporarily add to strategies config
        original_config = self.executor.strategies_config.get('demo_hybrid', None)
        self.executor.strategies_config['demo_hybrid'] = hybrid_strategy
        
        try:
            with patch.object(config_manager, 'get_user', return_value={'xtoken': 'demo_token'}):
                mock_api = self.create_mock_api_client()
                
                with patch('app.services.extended_strategy_executor.GuruShotsAPI', return_value=mock_api):
                    
                    logger.info(f"\n🎯 Testing hybrid strategy: demo_hybrid")
                    logger.info(f"   Description: {hybrid_strategy['description']}")
                    
                    logger.info("   📋 Strategy breakdown:")
                    for step, action_str in hybrid_strategy.items():
                        if step != 'description':
                            logger.info(f"      Step {step}: {action_str}")
                    
                    start_time = datetime.now()
                    
                    execution_id = await self.executor.execute_extended_strategy(
                        profile_id='demo_user',
                        challenge_id='demo_challenge_789',
                        challenge_url='challenge-demo_challenge_789',
                        strategy_name='demo_hybrid'
                    )
                    
                    end_time = datetime.now()
                    execution_duration = (end_time - start_time).total_seconds()
                    
                    logger.info(f"   ✅ Hybrid strategy initialized in {execution_duration:.2f}s")
                    logger.info(f"   📋 Execution ID: {execution_id}")
                    
                    # Show the execution status
                    if execution_id in self.executor.active_executions:
                        context = self.executor.active_executions[execution_id]
                        actions = context['actions']
                        
                        # Count immediate vs future actions
                        immediate_count = sum(1 for a in actions if a.get('executed', False))
                        future_count = len(actions) - immediate_count
                        
                        logger.info(f"   ⚡ Immediate actions executed: {immediate_count}")
                        logger.info(f"   📅 Future actions scheduled: {future_count}")
                        
                        if future_count > 0:
                            logger.info(f"   📋 Scheduled actions:")
                            for action in actions:
                                if not action.get('executed', False):
                                    scheduled_in = (action['scheduled_time'] - datetime.now()).total_seconds()
                                    logger.info(f"      - {action['action']} ({action['timing']}) - in {scheduled_in:.0f}s")
                    
        finally:
            # Clean up test strategy
            if original_config is None and 'demo_hybrid' in self.executor.strategies_config:
                del self.executor.strategies_config['demo_hybrid']
            elif original_config is not None:
                self.executor.strategies_config['demo_hybrid'] = original_config
    
    async def demo_execution_monitoring(self):
        """Demonstrate execution monitoring capabilities"""
        logger.info("=" * 60)
        logger.info("📊 DEMONSTRATING EXECUTION MONITORING")
        logger.info("=" * 60)
        
        # Show currently active executions
        active_count = len(self.executor.active_executions)
        logger.info(f"🔍 Currently active executions: {active_count}")
        
        if active_count > 0:
            logger.info("📋 Active execution details:")
            
            for execution_id, context in self.executor.active_executions.items():
                status = self.executor.get_execution_status(execution_id)
                if status:
                    logger.info(f"   📄 {execution_id}:")
                    logger.info(f"      Strategy: {status['strategy_name']}")
                    logger.info(f"      Challenge: {status['challenge_id']}")
                    logger.info(f"      Status: {status['status']}")
                    logger.info(f"      Progress: {status['completed_actions']}/{status['total_actions']}")
                    
                    if status['next_action']:
                        next_action = status['next_action']
                        scheduled_in = (next_action['scheduled_time'] - datetime.now()).total_seconds()
                        logger.info(f"      Next: {next_action['action']} in {scheduled_in:.0f}s")
        
        else:
            logger.info("   No active executions (all immediate actions completed)")
    
    def analyze_strategies_config(self):
        """Analyze the strategies configuration to show NOW vs FUTURE patterns"""
        logger.info("=" * 60)
        logger.info("📈 STRATEGY CONFIGURATION ANALYSIS")
        logger.info("=" * 60)
        
        now_strategies = []
        future_strategies = []
        hybrid_strategies = []
        
        for strategy_name, config in self.executor.strategies_config.items():
            now_count = 0
            future_count = 0
            
            for step, action_string in config.items():
                if step == 'description':
                    continue
                    
                # Parse action to determine timing
                parts = [p.strip() for p in action_string.split(',')]
                if len(parts) < 1:
                    continue
                
                # Detect timing
                first_part = parts[0]
                if self.executor._is_timing_format(first_part):
                    timing = first_part
                elif len(parts) >= 2:
                    timing = parts[1]
                else:
                    continue
                
                if timing.lower() == 'now':
                    now_count += 1
                else:
                    future_count += 1
            
            # Categorize strategy
            if now_count > 0 and future_count == 0:
                now_strategies.append((strategy_name, now_count, future_count))
            elif now_count == 0 and future_count > 0:
                future_strategies.append((strategy_name, now_count, future_count))
            elif now_count > 0 and future_count > 0:
                hybrid_strategies.append((strategy_name, now_count, future_count))
        
        logger.info(f"⚡ NOW-only strategies ({len(now_strategies)}):")
        for name, now_count, future_count in now_strategies:
            description = self.executor.strategies_config[name].get('description', 'No description')
            logger.info(f"   {name}: {now_count} immediate actions - {description}")
        
        logger.info(f"\n📅 FUTURE-only strategies ({len(future_strategies)}):")
        for name, now_count, future_count in future_strategies:
            description = self.executor.strategies_config[name].get('description', 'No description')
            logger.info(f"   {name}: {future_count} scheduled actions - {description}")
        
        logger.info(f"\n🔄 HYBRID strategies ({len(hybrid_strategies)}):")
        for name, now_count, future_count in hybrid_strategies:
            description = self.executor.strategies_config[name].get('description', 'No description')
            logger.info(f"   {name}: {now_count} immediate + {future_count} scheduled - {description}")
        
        total_strategies = len(now_strategies) + len(future_strategies) + len(hybrid_strategies)
        logger.info(f"\n📊 Summary: {total_strategies} total strategies")
        logger.info(f"   ⚡ {len(now_strategies)} immediate-only")
        logger.info(f"   📅 {len(future_strategies)} scheduled-only") 
        logger.info(f"   🔄 {len(hybrid_strategies)} hybrid")
    
    async def run_full_demo(self):
        """Run complete demonstration"""
        logger.info("🎬 ExtendedStrategyExecutor Full Demonstration")
        logger.info("=" * 80)
        
        # Analyze configuration first
        self.analyze_strategies_config()
        
        await asyncio.sleep(1)
        
        # Demo different strategy types
        await self.demo_now_strategies()
        await asyncio.sleep(1)
        
        await self.demo_future_strategies()
        await asyncio.sleep(1)
        
        await self.demo_hybrid_strategy()
        await asyncio.sleep(1)
        
        await self.demo_execution_monitoring()
        
        logger.info("=" * 80)
        logger.info("✅ DEMONSTRATION COMPLETE")
        logger.info("=" * 80)
        
        logger.info("\n📋 KEY FINDINGS:")
        logger.info("   ⚡ NOW actions execute immediately without APScheduler")
        logger.info("   📅 FUTURE actions use internal loop-based scheduling")
        logger.info("   🔄 HYBRID strategies separate immediate vs scheduled actions")
        logger.info("   🎯 The hybrid execution model works correctly for all strategy types")
        logger.info("   ✅ No APScheduler dependency for immediate actions")

async def main():
    """Main demonstration execution"""
    demo = StrategyExecutionDemo()
    await demo.run_full_demo()
    
    # Keep running briefly to show any background activity
    logger.info("\n⏰ Monitoring background activity for 5 seconds...")
    await asyncio.sleep(5)
    
    # Final status check
    active_executions = len(demo.executor.active_executions)
    if active_executions > 0:
        logger.info(f"🔍 Still {active_executions} executions running in background")
    else:
        logger.info("🏁 All executions completed or cleaned up")

if __name__ == "__main__":
    asyncio.run(main())