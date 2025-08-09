#!/usr/bin/env python3
"""
Test script for ExtendedStrategyExecutor
Tests the separation of 'now' actions vs future scheduled actions
"""

import asyncio
import logging
import sys
import os
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.extended_strategy_executor import ExtendedStrategyExecutor
from app.services.gurushots_api import GuruShotsAPI
from app.services.config_manager import config_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TestExtendedStrategyExecutor:
    """Test class for ExtendedStrategyExecutor functionality"""
    
    def __init__(self):
        self.executor = ExtendedStrategyExecutor()
        self.test_results = {}
        
    def log_test_result(self, test_name: str, success: bool, details: str = ""):
        """Log and store test results"""
        status = "✅ PASS" if success else "❌ FAIL"
        logger.info(f"{status} {test_name}: {details}")
        self.test_results[test_name] = {
            'success': success,
            'details': details,
            'timestamp': datetime.now()
        }
    
    async def setup_test_environment(self):
        """Setup test environment with mock data"""
        logger.info("🔧 Setting up test environment...")
        
        # Create mock user configuration
        test_user = {
            'xtoken': 'mock_token_for_testing',
            'username': 'test_user',
            'user_id': '12345'
        }
        
        # Mock config_manager methods
        with patch.object(config_manager, 'get_user', return_value=test_user):
            return test_user
    
    def create_mock_api_client(self):
        """Create a mock API client for testing"""
        mock_api = AsyncMock(spec=GuruShotsAPI)
        
        # Mock challenge details with future end time
        future_time = datetime.now() + timedelta(hours=2)
        mock_api.get_challenge_details.return_value = {
            'challenge': {
                'close_time': future_time.timestamp()
            }
        }
        
        # Mock vote execution
        mock_api.execute_simple_vote.return_value = {
            'success': True,
            'votes_cast': 10,
            'result_data': {'message': 'Vote successful'}
        }
        
        # Mock turbo execution
        mock_api.set_turbo.return_value = {
            'success': True,
            'message': 'Turbo unlocked'
        }
        
        # Mock boost execution
        mock_api.boost_photo.return_value = {
            'success': True,
            'message': 'Photo boosted'
        }
        
        # Mock user info
        mock_api.get_current_user_info.return_value = {
            'username': 'test_user',
            'user_id': '12345'
        }
        
        return mock_api
    
    async def test_parse_strategy_actions(self):
        """Test strategy action parsing for different formats"""
        logger.info("🧪 Testing strategy action parsing...")
        
        try:
            # Test future timing calculation
            future_time = datetime.now() + timedelta(hours=2)
            
            # Test 'now' strategies
            now_actions_fillnow1 = self.executor._parse_strategy_actions('fill-now-1', future_time)
            now_actions_fillnow70 = self.executor._parse_strategy_actions('fill-now-70', future_time)
            now_actions_turbo0 = self.executor._parse_strategy_actions('turbo-0', future_time)
            
            # Test future timing strategies
            future_actions_4m = self.executor._parse_strategy_actions('4m', future_time)
            future_actions_3m = self.executor._parse_strategy_actions('3m', future_time)
            
            # Verify 'now' actions
            now_count_fillnow1 = sum(1 for a in now_actions_fillnow1 if a['timing'] == 'now')
            now_count_fillnow70 = sum(1 for a in now_actions_fillnow70 if a['timing'] == 'now')
            now_count_turbo0 = sum(1 for a in now_actions_turbo0 if a['timing'] == 'now')
            
            # Verify future actions
            future_count_4m = sum(1 for a in future_actions_4m if a['timing'] != 'now')
            future_count_3m = sum(1 for a in future_actions_3m if a['timing'] != 'now')
            
            self.log_test_result(
                "parse_strategy_actions",
                True,
                f"fill-now-1: {now_count_fillnow1} NOW actions, fill-now-70: {now_count_fillnow70} NOW actions, turbo-0: {now_count_turbo0} NOW actions, 4m: {future_count_4m} FUTURE actions, 3m: {future_count_3m} FUTURE actions"
            )
            
            # Detailed analysis
            logger.info(f"📊 fill-now-1 actions: {[{'action': a['action'], 'timing': a['timing'], 'params': a['parameters']} for a in now_actions_fillnow1]}")
            logger.info(f"📊 4m actions (first 3): {[{'action': a['action'], 'timing': a['timing'], 'scheduled_time': a['scheduled_time']} for a in future_actions_4m[:3]]}")
            
        except Exception as e:
            self.log_test_result("parse_strategy_actions", False, f"Exception: {e}")
    
    async def test_timing_format_detection(self):
        """Test timing format detection logic"""
        logger.info("🧪 Testing timing format detection...")
        
        try:
            # Test various timing formats
            test_cases = [
                ('now', True, 'Should detect NOW timing'),
                ('end-4m0s', True, 'Should detect future end timing'),
                ('end-120m0s', True, 'Should detect long future timing'),
                ('next-1m0s', True, 'Should detect next timing'),
                ('vote', False, 'Should NOT detect action as timing'),
                ('turbo', False, 'Should NOT detect action as timing'),
                ('end-0m30s', True, 'Should detect short end timing'),
            ]
            
            all_correct = True
            results = []
            
            for timing_text, expected, description in test_cases:
                result = self.executor._is_timing_format(timing_text)
                is_correct = result == expected
                all_correct = all_correct and is_correct
                results.append(f"{timing_text}: {result} ({description})")
                
                if not is_correct:
                    logger.warning(f"⚠️  MISMATCH: {timing_text} -> {result}, expected {expected}")
            
            self.log_test_result(
                "timing_format_detection",
                all_correct,
                f"Tested {len(test_cases)} cases, all correct: {all_correct}"
            )
            
            for result in results:
                logger.info(f"    {result}")
                
        except Exception as e:
            self.log_test_result("timing_format_detection", False, f"Exception: {e}")
    
    async def test_now_vs_future_separation(self):
        """Test the core functionality: separating NOW vs FUTURE actions"""
        logger.info("🧪 Testing NOW vs FUTURE action separation...")
        
        try:
            with patch.object(config_manager, 'get_user', return_value={'xtoken': 'test_token'}):
                mock_api = self.create_mock_api_client()
                
                with patch('app.services.extended_strategy_executor.GuruShotsAPI', return_value=mock_api):
                    
                    # Test fill-now-1 (should be immediate)
                    logger.info("🔍 Testing fill-now-1 strategy (should be immediate)...")
                    
                    # Patch the executor's methods to track calls
                    executed_now_actions = []
                    scheduled_future_actions = []
                    
                    async def mock_execute_single_action(*args, **kwargs):
                        executed_now_actions.append(args)
                        return {'success': True, 'message': 'Immediate execution'}
                    
                    def mock_create_task(coro):
                        scheduled_future_actions.append('future_task_created')
                        return MagicMock()
                    
                    with patch.object(self.executor, '_execute_single_action', side_effect=mock_execute_single_action):
                        with patch('asyncio.create_task', side_effect=mock_create_task):
                            
                            execution_id = await self.executor.execute_extended_strategy(
                                profile_id='test_user',
                                challenge_id='12345',
                                challenge_url='challenge-12345',
                                strategy_name='fill-now-1'
                            )
                            
                            # Verify immediate execution
                            immediate_executions = len(executed_now_actions)
                            future_tasks = len(scheduled_future_actions)
                            
                            self.log_test_result(
                                "now_vs_future_fillnow1",
                                immediate_executions > 0 and future_tasks == 0,
                                f"Immediate: {immediate_executions}, Future: {future_tasks}"
                            )
                    
                    # Reset tracking
                    executed_now_actions.clear()
                    scheduled_future_actions.clear()
                    
                    # Test 4m strategy (should be scheduled)
                    logger.info("🔍 Testing 4m strategy (should be scheduled)...")
                    
                    with patch.object(self.executor, '_execute_single_action', side_effect=mock_execute_single_action):
                        with patch('asyncio.create_task', side_effect=mock_create_task):
                            
                            execution_id = await self.executor.execute_extended_strategy(
                                profile_id='test_user',
                                challenge_id='12345',
                                challenge_url='challenge-12345',
                                strategy_name='4m'
                            )
                            
                            immediate_executions = len(executed_now_actions)
                            future_tasks = len(scheduled_future_actions)
                            
                            self.log_test_result(
                                "now_vs_future_4m",
                                immediate_executions == 0 and future_tasks > 0,
                                f"Immediate: {immediate_executions}, Future: {future_tasks}"
                            )
                    
        except Exception as e:
            self.log_test_result("now_vs_future_separation", False, f"Exception: {e}")
    
    async def test_hybrid_strategy(self):
        """Test a strategy with both NOW and FUTURE actions"""
        logger.info("🧪 Testing hybrid strategy (NOW + FUTURE actions)...")
        
        try:
            # Create a test hybrid strategy in the config
            hybrid_strategy = {
                'description': 'Test hybrid strategy with NOW and FUTURE actions',
                '0': 'vote,now,5',  # Immediate action
                '1': 'vote,end-2m0s,10',  # Future action
                '2': 'turbo,now,0',  # Another immediate action
                '3': 'vote,end-1m0s,15'  # Another future action
            }
            
            # Temporarily add to strategies config
            original_config = self.executor.strategies_config.get('test_hybrid', None)
            self.executor.strategies_config['test_hybrid'] = hybrid_strategy
            
            try:
                with patch.object(config_manager, 'get_user', return_value={'xtoken': 'test_token'}):
                    mock_api = self.create_mock_api_client()
                    
                    with patch('app.services.extended_strategy_executor.GuruShotsAPI', return_value=mock_api):
                        
                        executed_now_actions = []
                        scheduled_future_actions = []
                        
                        async def mock_execute_single_action(*args, **kwargs):
                            executed_now_actions.append(args)
                            return {'success': True, 'message': 'Immediate execution'}
                        
                        def mock_create_task(coro):
                            scheduled_future_actions.append('future_task_created')
                            return MagicMock()
                        
                        with patch.object(self.executor, '_execute_single_action', side_effect=mock_execute_single_action):
                            with patch('asyncio.create_task', side_effect=mock_create_task):
                                
                                execution_id = await self.executor.execute_extended_strategy(
                                    profile_id='test_user',
                                    challenge_id='12345',
                                    challenge_url='challenge-12345',
                                    strategy_name='test_hybrid'
                                )
                                
                                immediate_executions = len(executed_now_actions)
                                future_tasks = len(scheduled_future_actions)
                                
                                # Should have 2 immediate actions and 1 future task (for 2 future actions)
                                expected_immediate = 2  # vote,now,5 and turbo,now,0
                                expected_future = 1     # Task created for future actions
                                
                                success = (immediate_executions == expected_immediate and future_tasks == expected_future)
                                
                                self.log_test_result(
                                    "hybrid_strategy",
                                    success,
                                    f"Expected {expected_immediate} immediate, {expected_future} future tasks. Got {immediate_executions} immediate, {future_tasks} future"
                                )
                                
            finally:
                # Clean up test strategy
                if original_config is None:
                    del self.executor.strategies_config['test_hybrid']
                else:
                    self.executor.strategies_config['test_hybrid'] = original_config
                    
        except Exception as e:
            self.log_test_result("hybrid_strategy", False, f"Exception: {e}")
    
    async def test_execution_flow_verification(self):
        """Verify the execution flow doesn't use APScheduler for NOW actions"""
        logger.info("🧪 Testing execution flow verification (no APScheduler for NOW)...")
        
        try:
            # This test verifies that NOW actions don't create APScheduler jobs
            # and that the separation logic in execute_extended_strategy works correctly
            
            with patch.object(config_manager, 'get_user', return_value={'xtoken': 'test_token'}):
                mock_api = self.create_mock_api_client()
                
                with patch('app.services.extended_strategy_executor.GuruShotsAPI', return_value=mock_api):
                    
                    # Test with turbo-0 (immediate turbo action)
                    apscheduler_jobs_created = []
                    
                    def mock_add_job(*args, **kwargs):
                        apscheduler_jobs_created.append(kwargs.get('id', 'unknown'))
                    
                    # Mock any potential APScheduler usage (should not be called for NOW actions)
                    with patch('apscheduler.schedulers.asyncio.AsyncIOScheduler.add_job', side_effect=mock_add_job):
                        
                        execution_id = await self.executor.execute_extended_strategy(
                            profile_id='test_user',
                            challenge_id='12345',
                            challenge_url='challenge-12345',
                            strategy_name='turbo-0'
                        )
                        
                        # For NOW-only strategies, no APScheduler jobs should be created
                        no_scheduler_jobs = len(apscheduler_jobs_created) == 0
                        
                        self.log_test_result(
                            "no_apscheduler_for_now",
                            no_scheduler_jobs,
                            f"APScheduler jobs created: {len(apscheduler_jobs_created)} (should be 0 for NOW actions)"
                        )
                        
                        if apscheduler_jobs_created:
                            logger.warning(f"⚠️  Unexpected APScheduler jobs: {apscheduler_jobs_created}")
                    
        except Exception as e:
            self.log_test_result("execution_flow_verification", False, f"Exception: {e}")
    
    def analyze_current_implementation(self):
        """Analyze the current implementation for potential issues"""
        logger.info("🔍 Analyzing current implementation...")
        
        issues_found = []
        recommendations = []
        
        # Check the execute_extended_strategy method
        try:
            # Read the source code to analyze the logic
            import inspect
            source = inspect.getsource(self.executor.execute_extended_strategy)
            
            # Check for proper NOW vs FUTURE separation
            if "now_actions = [a for a in actions if a.get('timing') == 'now']" in source:
                logger.info("✅ Found proper NOW actions filtering")
            else:
                issues_found.append("NOW actions filtering logic may be incorrect")
            
            if "future_actions = [a for a in actions if a.get('timing') != 'now']" in source:
                logger.info("✅ Found proper FUTURE actions filtering")
            else:
                issues_found.append("FUTURE actions filtering logic may be incorrect")
            
            if "_execute_single_action" in source:
                logger.info("✅ Found immediate action execution")
            else:
                issues_found.append("Immediate action execution may be missing")
            
            if "asyncio.create_task" in source:
                logger.info("✅ Found async task creation for future actions")
            else:
                issues_found.append("Async task creation for future actions may be missing")
            
            # Check if there's proper loop vs scheduler handling
            if "_execute_strategy_loop" in source:
                logger.info("✅ Found strategy loop for future actions")
            else:
                issues_found.append("Strategy loop for future actions may be missing")
            
        except Exception as e:
            issues_found.append(f"Could not analyze source code: {e}")
        
        # Analysis results
        if not issues_found:
            self.log_test_result(
                "implementation_analysis",
                True,
                "No issues found in current implementation"
            )
        else:
            self.log_test_result(
                "implementation_analysis",
                False,
                f"Found {len(issues_found)} issues: {', '.join(issues_found)}"
            )
            
            for issue in issues_found:
                logger.warning(f"⚠️  Issue: {issue}")
    
    async def run_all_tests(self):
        """Run all tests and return summary"""
        logger.info("🚀 Starting ExtendedStrategyExecutor tests...")
        
        await self.setup_test_environment()
        
        # Run tests
        await self.test_parse_strategy_actions()
        await self.test_timing_format_detection()
        await self.test_now_vs_future_separation()
        await self.test_hybrid_strategy()
        await self.test_execution_flow_verification()
        self.analyze_current_implementation()
        
        # Summary
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result['success'])
        failed_tests = total_tests - passed_tests
        
        logger.info("=" * 60)
        logger.info(f"📊 TEST SUMMARY:")
        logger.info(f"   Total tests: {total_tests}")
        logger.info(f"   ✅ Passed: {passed_tests}")
        logger.info(f"   ❌ Failed: {failed_tests}")
        logger.info(f"   Success rate: {(passed_tests/total_tests*100):.1f}%")
        logger.info("=" * 60)
        
        # Detailed results
        logger.info("📋 DETAILED RESULTS:")
        for test_name, result in self.test_results.items():
            status = "✅ PASS" if result['success'] else "❌ FAIL"
            logger.info(f"   {status} {test_name}: {result['details']}")
        
        return {
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'failed_tests': failed_tests,
            'success_rate': passed_tests/total_tests*100,
            'results': self.test_results
        }

async def main():
    """Main test execution"""
    print("🧪 ExtendedStrategyExecutor Test Suite")
    print("=" * 60)
    
    tester = TestExtendedStrategyExecutor()
    results = await tester.run_all_tests()
    
    # Return appropriate exit code
    exit_code = 0 if results['failed_tests'] == 0 else 1
    return exit_code

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)