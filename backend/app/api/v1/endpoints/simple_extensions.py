"""
Simple API endpoints for ANCA surveillance and extended strategies
"""

from fastapi import APIRouter, HTTPException
from typing import Optional, Dict, Any
import logging

from app.services.simple_anca_surveillance import simple_anca_surveillance, anca_surveillance_cron_job
from app.services.extended_strategy_executor import extended_strategy_executor
from app.services.config_manager import config_manager

logger = logging.getLogger(__name__)
router = APIRouter()

# ANCA Surveillance Endpoints

@router.post("/anca/surveillance/run")
async def run_anca_surveillance(user_token: Optional[str] = None):
    """Run ANCA surveillance manually (normally called by cron)"""
    try:
        if not user_token:
            # Get first available user token
            users = config_manager.get_all_users()
            if users:
                user_token = list(users.values())[0].get('xtoken')
        
        if not user_token:
            raise HTTPException(status_code=400, detail="No user token available")
        
        results = await simple_anca_surveillance.monitor_active_challenges(user_token)
        return results
        
    except Exception as e:
        logger.error(f"Error running ANCA surveillance: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/anca/events")
async def get_anca_events(limit: int = 50):
    """Get recent ANCA events"""
    try:
        events = simple_anca_surveillance.get_recent_events(limit)
        return {"events": events, "total": len(events)}
    except Exception as e:
        logger.error(f"Error getting ANCA events: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/anca/stats")
async def get_anca_stats():
    """Get ANCA surveillance statistics"""
    try:
        stats = simple_anca_surveillance.get_stats()
        return stats
    except Exception as e:
        logger.error(f"Error getting ANCA stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Extended Strategy Endpoints

@router.post("/strategies/extended/execute")
async def execute_extended_strategy(
    profile_id: str,
    challenge_id: str,
    challenge_url: str,
    strategy_name: str
):
    """
    Execute an extended strategy from strategies.ini
    
    Example: strategy_name = "4photos" for the [4photos] section
    """
    try:
        execution_id = await extended_strategy_executor.execute_extended_strategy(
            profile_id=profile_id,
            challenge_id=challenge_id,
            challenge_url=challenge_url,
            strategy_name=strategy_name
        )
        
        return {
            "success": True,
            "execution_id": execution_id,
            "message": f"Started extended strategy '{strategy_name}'"
        }
        
    except Exception as e:
        logger.error(f"Error executing extended strategy: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/strategies/extended/{execution_id}/status")
async def get_extended_strategy_status(execution_id: str):
    """Get status of extended strategy execution"""
    try:
        status = extended_strategy_executor.get_execution_status(execution_id)
        
        if not status:
            raise HTTPException(status_code=404, detail="Execution not found")
        
        return status
        
    except Exception as e:
        logger.error(f"Error getting strategy status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/strategies/extended/{execution_id}/cancel")
async def cancel_extended_strategy(execution_id: str):
    """Cancel extended strategy execution"""
    try:
        success = await extended_strategy_executor.cancel_execution(execution_id)
        
        if success:
            return {"success": True, "message": f"Execution {execution_id} cancelled"}
        else:
            raise HTTPException(status_code=404, detail="Execution not found")
        
    except Exception as e:
        logger.error(f"Error cancelling strategy: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/strategies/available")
async def get_available_strategies():
    """Get list of available strategies from strategies.ini"""
    try:
        strategies = []
        
        for name, config in extended_strategy_executor.strategies_config.items():
            if name == 'DEFAULT':
                continue
                
            actions_count = len([k for k in config.keys() if k.isdigit()])
            strategies.append({
                "name": name,
                "description": config.get('description', ''),
                "actions_count": actions_count,
                "actions": [
                    f"{step}: {config[step]}" 
                    for step in sorted([k for k in config.keys() if k.isdigit()], key=int)
                ]
            })
        
        return {"strategies": strategies}
        
    except Exception as e:
        logger.error(f"Error getting available strategies: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/strategies/test-photo-index")
async def test_photo_index_resolution(
    profile_id: str,
    challenge_id: int
):
    """
    Test photo index resolution for debugging
    Shows which photos correspond to index [0], [1], etc.
    """
    try:
        result = await extended_strategy_executor.test_photo_index_resolution(
            profile_id=profile_id,
            challenge_id=challenge_id
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error testing photo index resolution: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/strategies/debug/photo-indices/{profile_id}/{challenge_id}")
async def debug_photo_indices(profile_id: str, challenge_id: int):
    """
    Debug endpoint to see photo indices for a user in a challenge
    Shows mapping of [0], [1], etc. to actual photo IDs and votes
    """
    try:
        result = await extended_strategy_executor.test_photo_index_resolution(profile_id, challenge_id)
        
        if not result.get('success'):
            return result
        
        # Create a more readable debug format
        photos = result.get('photos', [])
        debug_info = {
            'challenge_id': challenge_id,
            'user': result.get('user_info', {}),
            'photo_count': len(photos),
            'index_mapping': {},
            'boost_command_examples': {},
            'turbo_command_examples': {}
        }
        
        for photo in photos:
            index = photo['index']
            debug_info['index_mapping'][f'[{index}]'] = {
                'photo_id': photo['photo_id'],
                'votes': photo['votes'],
                'boost_status': photo['boost_status'],
                'guru_pick': photo['guru_pick']
            }
            
            # Generate example commands
            debug_info['boost_command_examples'][f'boost,end-50m0s,{index}'] = f"Boost photo {photo['photo_id']} ({photo['votes']} votes)"
            debug_info['turbo_command_examples'][f'turbo,end-50m0s,{index}'] = f"Turbo targeting photo {photo['photo_id']} ({photo['votes']} votes)"
        
        return debug_info
        
    except Exception as e:
        logger.error(f"Error in debug photo indices: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Cron Job Endpoint (for testing)

@router.post("/cron/anca-surveillance")
async def cron_anca_surveillance():
    """
    Endpoint to simulate cron job execution
    In practice, this would be called by your cron MCP
    """
    try:
        results = await anca_surveillance_cron_job()
        return {
            "cron_execution": "completed",
            "timestamp": "now",
            "results": results
        }
    except Exception as e:
        logger.error(f"Error in cron ANCA surveillance: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
