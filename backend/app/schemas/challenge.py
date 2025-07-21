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