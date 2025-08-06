"""
API endpoints for swap and competitor tracking functionality
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
import logging

from app.services.gurushots_api import GuruShotsAPI
from app.services.competitor_tracker import get_competitor_tracker
from app.schemas.challenge import SwapRequest, CompetitorTrackingRequest
from app.websockets.connection_manager import connection_manager

logger = logging.getLogger(__name__)
router = APIRouter()

# Dependency to get current user (placeholder - implement based on your auth system)
async def get_current_user():
    return {"user_id": "default_user", "token": "default_token"}

@router.post("/swap")
async def swap_photo(
    swap_request: SwapRequest,
    current_user = Depends(get_current_user)
):
    """
    Swap a photo in a challenge
    """
    try:
        api_client = GuruShotsAPI(current_user["token"])
        
        result = await api_client.swap_photo(
            challenge_id=swap_request.challenge_id,
            current_photo_id=swap_request.current_photo_id,
            new_photo_id=swap_request.new_photo_id
        )
        
        # Notify via WebSocket
        await connection_manager.notify_swap_executed(
            current_user["user_id"], 
            swap_request.challenge_id,
            result.get("success", False),
            swap_request.current_photo_id,
            swap_request.new_photo_id
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error in swap_photo endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/followings/{challenge_id}")
async def get_challenge_followings(
    challenge_id: int,
    limit: int = 200,
    start: int = 0,
    current_user = Depends(get_current_user)
):
    """
    Get followings participating in a challenge
    """
    try:
        api_client = GuruShotsAPI(current_user["token"])
        
        result = await api_client.get_challenge_followings(
            challenge_id=challenge_id,
            limit=limit,
            start=start
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error in get_challenge_followings endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/tracking/start")
async def start_competitor_tracking(
    tracking_request: CompetitorTrackingRequest,
    current_user = Depends(get_current_user)
):
    """
    Start tracking competitors in a challenge
    """
    try:
        api_client = GuruShotsAPI(current_user["token"])
        tracker = get_competitor_tracker(api_client)
        
        success = await tracker.start_tracking_challenge(
            challenge_id=tracking_request.challenge_id,
            challenge_url=tracking_request.challenge_url,
            competitors=tracking_request.competitors
        )
        
        if success:
            # Notify via WebSocket
            await connection_manager.send_personal_message(
                current_user["user_id"],
                {
                    "type": "tracking_started",
                    "challenge_id": tracking_request.challenge_id,
                    "message": f"Started tracking challenge {tracking_request.challenge_id}"
                }
            )
            
            return {"success": True, "message": "Tracking started successfully"}
        else:
            raise HTTPException(status_code=400, detail="Failed to start tracking")
            
    except Exception as e:
        logger.error(f"Error in start_competitor_tracking endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/tracking/stop/{challenge_id}")
async def stop_competitor_tracking(
    challenge_id: int,
    current_user = Depends(get_current_user)
):
    """
    Stop tracking competitors in a challenge
    """
    try:
        api_client = GuruShotsAPI(current_user["token"])
        tracker = get_competitor_tracker(api_client)
        
        await tracker.stop_tracking_challenge(challenge_id)
        
        # Notify via WebSocket
        await connection_manager.send_personal_message(
            current_user["user_id"],
            {
                "type": "tracking_stopped", 
                "challenge_id": challenge_id,
                "message": f"Stopped tracking challenge {challenge_id}"
            }
        )
        
        return {"success": True, "message": "Tracking stopped successfully"}
        
    except Exception as e:
        logger.error(f"Error in stop_competitor_tracking endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tracking/status")
async def get_tracking_status(current_user = Depends(get_current_user)):
    """
    Get status of all tracking sessions
    """
    try:
        api_client = GuruShotsAPI(current_user["token"])
        tracker = get_competitor_tracker(api_client)
        
        status = tracker.get_tracking_status()
        return status
        
    except Exception as e:
        logger.error(f"Error in get_tracking_status endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tracking/competitors/{challenge_id}")
async def get_competitor_data(
    challenge_id: int,
    user_name: Optional[str] = None,
    current_user = Depends(get_current_user)
):
    """
    Get competitor data for a challenge
    """
    try:
        api_client = GuruShotsAPI(current_user["token"])
        tracker = get_competitor_tracker(api_client)
        
        data = tracker.get_competitor_data(challenge_id, user_name)
        return data
        
    except Exception as e:
        logger.error(f"Error in get_competitor_data endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/challenge/{challenge_url}/details")
async def get_challenge_details(
    challenge_url: str,
    current_user = Depends(get_current_user)
):
    """
    Get detailed challenge information including timing
    """
    try:
        api_client = GuruShotsAPI(current_user["token"])
        
        result = await api_client.get_challenge_details(challenge_url)
        return result
        
    except Exception as e:
        logger.error(f"Error in get_challenge_details endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
