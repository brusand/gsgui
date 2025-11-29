"""
Pydantic schemas for Challenge API endpoints
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


class ChallengeBase(BaseModel):
    """Base schema for Challenge"""
    title: str
    url: str
    end_time: datetime
    votes: int = 0
    rank: int = 0
    level: Optional[str] = None
    exposure: int = 0
    gps: int = 0


class ChallengeCreate(ChallengeBase):
    """Schema for creating a Challenge"""
    id: str
    challenge_data: Dict[str, Any]


class ChallengeUpdate(BaseModel):
    """Schema for updating a Challenge"""
    title: Optional[str] = None
    votes: Optional[int] = None
    rank: Optional[int] = None
    level: Optional[str] = None
    exposure: Optional[int] = None
    selected_strategy: Optional[str] = None
    status: Optional[str] = None
    turbo_status: Optional[str] = None
    boost_status: Optional[str] = None

class ChallengeResponse(ChallengeBase):
    """Schema for Challenge API responses"""
    id: str
    time_left_days: int
    time_left_hours: int
    time_left_minutes: int
    time_left_seconds: int
    selected_strategy: Optional[str] = None
    status: str
    turbo_status: str
    boost_status: str
    current_process_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    user_id: str
    
    class Config:
        from_attributes = True


class ChallengeListResponse(BaseModel):
    """Schema for Challenge list responses"""
    challenges: List[ChallengeResponse]
    total: int
    page: int = 1
    per_page: int = 100


class VotePanelRequest(BaseModel):
    """Schema for vote panel requests"""
    challenge_url: str
    limit: int = Field(default=100, ge=1, le=500)


class VotePanelResponse(BaseModel):
    """Schema for vote panel responses"""
    success: bool
    message: str = ""
    images: List[Dict[str, Any]] = []
    challenge_data: Dict[str, Any] = {}


class VoteRequest(BaseModel):
    """Schema for vote execution requests"""
    challenge_id: str
    vote_tokens: List[str]
    

class SimpleVoteRequest(BaseModel):
    """Schema for simple vote requests"""
    challenge_url: str
    vote_count: int = Field(ge=1, le=100)


class VoteResponse(BaseModel):
    """Schema for vote responses"""
    success: bool
    message: str
    result_data: Optional[Dict[str, Any]] = None



class SwapRequest(BaseModel):
    """Schema for photo swap requests"""
    challenge_id: int = Field(description="Challenge ID")
    current_photo_id: str = Field(description="Current photo ID to replace")
    new_photo_id: str = Field(description="New photo ID to use instead")


class SwapResponse(BaseModel):
    """Schema for photo swap responses"""
    success: bool
    message: str = ""
    challenge_id: int
    current_photo_id: str
    new_photo_id: str
    result_data: Optional[Dict[str, Any]] = None


class CompetitorTrackingRequest(BaseModel):
    """Schema for starting competitor tracking"""
    challenge_id: int = Field(description="Challenge ID to track")
    challenge_url: str = Field(description="Challenge URL")
    competitors: Optional[List[str]] = Field(
        default=None, 
        description="Specific competitor usernames to track (optional)"
    )


class CompetitorEvent(BaseModel):
    """Schema for competitor events"""
    type: str = Field(description="Event type: post, swap_out, boost")
    photo_id: str = Field(description="Photo ID involved in event")
    timestamp: str = Field(description="Event timestamp")
    votes: Optional[int] = Field(default=None, description="Photo votes at time of event")
    rank: Optional[int] = Field(default=None, description="User rank at time of event")
    previous_votes: Optional[int] = Field(default=None, description="Previous votes for swap events")


class CompetitorData(BaseModel):
    """Schema for competitor data"""
    user_id: int
    name: str
    entries: Dict[str, Any] = Field(description="Current photo entries")
    events: List[CompetitorEvent] = Field(description="List of detected events")
    stats: Dict[str, int] = Field(description="Statistics (swaps, posts, boosts)")


class TrackingStatus(BaseModel):
    """Schema for tracking session status"""
    active: bool
    url: str
    competitors_count: int
    start_time: str
    last_update: Optional[str] = None


class ChallengeDetails(BaseModel):
    """Schema for detailed challenge information"""
    success: bool
    challenge: Dict[str, Any] = Field(description="Challenge data")
    message: Optional[str] = None
    error: Optional[str] = None


class FollowingsRequest(BaseModel):
    """Schema for getting followings in challenge"""
    limit: int = Field(default=200, ge=1, le=500)
    start: int = Field(default=0, ge=0)


class FollowingsResponse(BaseModel):
    """Schema for followings response"""
    success: bool
    items: List[Dict[str, Any]] = Field(description="Following users data")
    message: Optional[str] = None
    error: Optional[str] = None



class AncaSurveillanceRequest(BaseModel):
    """Schema for starting ANCA surveillance"""
    challenge_ids: Optional[List[int]] = Field(
        default=None,
        description="Specific challenge IDs to monitor (optional, will monitor all active if not specified)"
    )


class StrategyExecutionRequest(BaseModel):
    """Schema for executing enhanced strategies"""
    strategy_name: str = Field(description="Name of strategy to execute")
    challenge_id: int = Field(description="Challenge ID")
    challenge_url: str = Field(description="Challenge URL")
    challenge_end_time: datetime = Field(description="Challenge end time for timing calculations")


class AncaEventResponse(BaseModel):
    """Schema for ANCA event data"""
    timestamp: str
    challenge_id: int
    event_type: str  # 'entry', 'swap', 'boost', 'rank_change'
    photo_id: Optional[str] = None
    votes: Optional[int] = None
    rank: Optional[int] = None
    time_left: Optional[str] = None
    additional_data: Optional[Dict[str, Any]] = None


class AncaPatternResponse(BaseModel):
    """Schema for ANCA behavioral patterns"""
    anca_username: str
    total_events: int
    event_breakdown: Dict[str, int]
    patterns: List[Dict[str, Any]]


class StrategyStatusResponse(BaseModel):
    """Schema for strategy execution status"""
    strategy_id: str
    strategy_name: str
    challenge_id: int
    status: str  # 'active', 'completed', 'failed', 'cancelled'
    started_at: str
    total_actions: int
    completed_actions: int
    successful_actions: int


class EnhancedStrategyAction(BaseModel):
    """Schema for enhanced strategy actions"""
    step: int
    action: str  # 'vote', 'submit', 'swap', 'boost', 'turbo', 'fill'
    timing: str  # 'end-2m0s', 'now', 'next-1h0s'
    parameters: List[str]
    scheduled_time: Optional[str] = None
    executed: bool = False
    result: Optional[Dict[str, Any]] = None


class AvailableStrategyResponse(BaseModel):
    """Schema for available strategy information"""
    name: str
    description: str
    actions_count: int
