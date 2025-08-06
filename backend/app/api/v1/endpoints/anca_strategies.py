"""
API endpoints for ANCA Intelligence and Enhanced Strategies
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional, Dict, Any
import logging

from app.services.gurushots_api import GuruShotsAPI
from app.services.anca_intelligence import get_anca_intelligence
from app.services.enhanced_strategy_engine import get_enhanced_strategy_engine
from app.schemas.challenge import AncaSurveillanceRequest, StrategyExecutionRequest
from app.websockets.connection_manager import connection_manager

logger = logging.getLogger(__name__)
router = APIRouter()

# Dependency to get current user (placeholder)
async def get_current_user():
    return {"user_id": "default_user", "token": "default_token"}

# ANCA Intelligence Endpoints

@router.post("/anca/surveillance/start")
async def start_anca_surveillance(
    surveillance_request: AncaSurveillanceRequest,
    current_user = Depends(get_current_user)
):
    """Start monitoring ANCA the vampire"""
    try:
        api_client = GuruShotsAPI(current_user["token"])
        anca_service = get_anca_intelligence(api_client, current_user["user_id"])
        
        success = await anca_service.start_surveillance(surveillance_request.challenge_ids)
        
        if success:
            return {
                "success": True,
                "message": f"Started ANCA surveillance for {len(surveillance_request.challenge_ids or [])} challenges",
                "anca_username": "anca.chilom"
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to start ANCA surveillance")
            
    except Exception as e:
        logger.error(f"Error starting ANCA surveillance: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/anca/surveillance/stop")
async def stop_anca_surveillance(current_user = Depends(get_current_user)):
    """Stop ANCA surveillance"""
    try:
        api_client = GuruShotsAPI(current_user["token"])
        anca_service = get_anca_intelligence(api_client, current_user["user_id"])
        
        anca_service.stop_surveillance()
        
        return {"success": True, "message": "ANCA surveillance stopped"}
        
    except Exception as e:
        logger.error(f"Error stopping ANCA surveillance: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/anca/events")
async def get_anca_events(
    challenge_id: Optional[int] = None,
    event_type: Optional[str] = None,
    limit: int = 100,
    current_user = Depends(get_current_user)
):
    """Get ANCA events with optional filters"""
    try:
        api_client = GuruShotsAPI(current_user["token"])
        anca_service = get_anca_intelligence(api_client, current_user["user_id"])
        
        events = anca_service.anca_events
        
        # Apply filters
        if challenge_id:
            events = [e for e in events if e.challenge_id == challenge_id]
        
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        
        # Limit results
        events = events[-limit:]
        
        return {
            "events": [
                {
                    "timestamp": event.timestamp,
                    "challenge_id": event.challenge_id,
                    "event_type": event.event_type,
                    "photo_id": event.photo_id,
                    "votes": event.votes,
                    "rank": event.rank,
                    "time_left": event.time_left,
                    "additional_data": event.additional_data
                }
                for event in events
            ],
            "total": len(events)
        }
        
    except Exception as e:
        logger.error(f"Error getting ANCA events: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/anca/patterns")
async def get_anca_patterns(current_user = Depends(get_current_user)):
    """Get detected ANCA behavioral patterns"""
    try:
        api_client = GuruShotsAPI(current_user["token"])
        anca_service = get_anca_intelligence(api_client, current_user["user_id"])
        
        # Get basic statistics
        events = anca_service.anca_events
        entry_events = [e for e in events if e.event_type == 'entry']
        swap_events = [e for e in events if e.event_type == 'swap']
        boost_events = [e for e in events if e.event_type == 'boost']
        
        return {
            "anca_username": "anca.chilom",
            "total_events": len(events),
            "event_breakdown": {
                "entries": len(entry_events),
                "swaps": len(swap_events),
                "boosts": len(boost_events),
                "rank_changes": len([e for e in events if e.event_type == 'rank_change'])
            },
            "patterns": [
                {
                    "pattern_type": "swap_frequency",
                    "description": "High swap frequency observed",
                    "confidence": 0.9 if len(swap_events) > 5 else 0.5
                },
                {
                    "pattern_type": "entry_timing",
                    "description": "Strategic entry timing patterns",
                    "confidence": 0.8 if len(entry_events) > 3 else 0.4
                }
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting ANCA patterns: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/anca/export")
async def export_anca_data(current_user = Depends(get_current_user)):
    """Export ANCA surveillance data"""
    try:
        api_client = GuruShotsAPI(current_user["token"])
        anca_service = get_anca_intelligence(api_client, current_user["user_id"])
        
        filepath = anca_service.export_anca_data()
        
        return {
            "success": True,
            "message": "ANCA data exported successfully",
            "filepath": filepath,
            "event_count": len(anca_service.anca_events)
        }
        
    except Exception as e:
        logger.error(f"Error exporting ANCA data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Enhanced Strategy Endpoints

@router.post("/strategies/execute")
async def execute_enhanced_strategy(
    execution_request: StrategyExecutionRequest,
    current_user = Depends(get_current_user)
):
    """Execute an enhanced strategy with new actions"""
    try:
        api_client = GuruShotsAPI(current_user["token"])
        strategy_engine = get_enhanced_strategy_engine(api_client, current_user["user_id"])
        
        strategy_id = await strategy_engine.execute_strategy(
            strategy_name=execution_request.strategy_name,
            challenge_id=execution_request.challenge_id,
            challenge_url=execution_request.challenge_url,
            challenge_end_time=execution_request.challenge_end_time
        )
        
        return {
            "success": True,
            "strategy_id": strategy_id,
            "message": f"Started strategy '{execution_request.strategy_name}'"
        }
        
    except Exception as e:
        logger.error(f"Error executing strategy: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/strategies/anca/create")
async def create_anca_strategy(
    strategy_type: str,  # "4images" or "single"
    current_user = Depends(get_current_user)
):
    """Create an ANCA-style strategy dynamically"""
    try:
        if strategy_type not in ["4images", "single"]:
            raise HTTPException(status_code=400, detail="Strategy type must be '4images' or 'single'")
        
        api_client = GuruShotsAPI(current_user["token"])
        strategy_engine = get_enhanced_strategy_engine(api_client, current_user["user_id"])
        
        strategy_name = strategy_engine.create_anca_strategy(strategy_type)
        
        return {
            "success": True,
            "strategy_name": strategy_name,
            "strategy_type": strategy_type,
            "message": f"Created ANCA {strategy_type} strategy"
        }
        
    except Exception as e:
        logger.error(f"Error creating ANCA strategy: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/strategies/{strategy_id}/status")
async def get_strategy_status(
    strategy_id: str,
    current_user = Depends(get_current_user)
):
    """Get status of a strategy execution"""
    try:
        api_client = GuruShotsAPI(current_user["token"])
        strategy_engine = get_enhanced_strategy_engine(api_client, current_user["user_id"])
        
        status = strategy_engine.get_strategy_status(strategy_id)
        
        if not status:
            raise HTTPException(status_code=404, detail="Strategy not found")
        
        return status
        
    except Exception as e:
        logger.error(f"Error getting strategy status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/strategies/{strategy_id}/cancel")
async def cancel_strategy(
    strategy_id: str,
    current_user = Depends(get_current_user)
):
    """Cancel an active strategy"""
    try:
        api_client = GuruShotsAPI(current_user["token"])
        strategy_engine = get_enhanced_strategy_engine(api_client, current_user["user_id"])
        
        success = await strategy_engine.cancel_strategy(strategy_id)
        
        if success:
            return {"success": True, "message": f"Strategy {strategy_id} cancelled"}
        else:
            raise HTTPException(status_code=404, detail="Strategy not found or already completed")
        
    except Exception as e:
        logger.error(f"Error cancelling strategy: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/strategies/available")
async def get_available_strategies(current_user = Depends(get_current_user)):
    """Get list of available strategies"""
    try:
        api_client = GuruShotsAPI(current_user["token"])
        strategy_engine = get_enhanced_strategy_engine(api_client, current_user["user_id"])
        
        strategies = []
        for name, config in strategy_engine.strategies.items():
            if name == 'DEFAULT':
                continue
                
            strategies.append({
                "name": name,
                "description": config.get('description', ''),
                "actions_count": len([k for k in config.keys() if k.isdigit()])
            })
        
        return {"strategies": strategies}
        
    except Exception as e:
        logger.error(f"Error getting available strategies: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
