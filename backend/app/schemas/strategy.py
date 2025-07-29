"""
Scheduled Strategy schemas for mobile app strategy management
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime
import re


class ScheduleStrategyRequest(BaseModel):
    """Request to schedule a strategy for a challenge"""
    challenge_id: str = Field(..., description="GuruShots challenge ID")
    strategy_name: str = Field(..., description="Strategy type (4m, fill, etc.)")
    challenge_title: Optional[str] = Field(None, description="Challenge title for display")
    scheduled_at: datetime = Field(..., description="When to execute the strategy")
    
    @validator('strategy_name')
    def validate_strategy_name(cls, v):
        valid_strategies = ['4m', 'fill', 'boost', 'swap']
        if v not in valid_strategies:
            raise ValueError(f'Strategy must be one of: {valid_strategies}')
        return v
    
    @validator('scheduled_at')
    def validate_scheduled_at(cls, v):
        if v <= datetime.now():
            raise ValueError('Scheduled time must be in the future')
        return v


class ScheduledStrategyResponse(BaseModel):
    """Response after scheduling a strategy"""
    strategy_id: str
    profile_id: str
    challenge_id: str
    strategy_name: str
    challenge_title: Optional[str]
    scheduled_at: datetime
    status: str  # 'pending', 'running', 'completed', 'failed', 'cancelled'
    created_at: datetime
    updated_at: Optional[datetime] = None


class StrategyListResponse(BaseModel):
    """List of scheduled strategies for a profile"""
    strategies: List[ScheduledStrategyResponse]
    total_count: int
    pending_count: int
    running_count: int


class StrategyUpdateRequest(BaseModel):
    """Request to update a scheduled strategy"""
    strategy_name: Optional[str] = Field(None, description="Change strategy type")
    scheduled_at: Optional[datetime] = Field(None, description="Reschedule execution time")
    status: Optional[str] = Field(None, description="Update status (cancel, etc.)")
    
    @validator('strategy_name')
    def validate_strategy_name(cls, v):
        if v is not None:
            valid_strategies = ['4m', 'fill', 'boost', 'swap']
            if v not in valid_strategies:
                raise ValueError(f'Strategy must be one of: {valid_strategies}')
        return v
    
    @validator('scheduled_at')
    def validate_scheduled_at(cls, v):
        if v is not None and v <= datetime.now():
            raise ValueError('Scheduled time must be in the future')
        return v
    
    @validator('status')
    def validate_status(cls, v):
        if v is not None:
            valid_statuses = ['pending', 'cancelled']
            if v not in valid_statuses:
                raise ValueError(f'Status can only be changed to: {valid_statuses}')
        return v


class AvailableStrategiesResponse(BaseModel):
    """List of available strategy types"""
    strategies: List[Dict[str, str]]  # [{"name": "4m", "description": "4-minute voting"}, ...]


class StrategyExecutionResult(BaseModel):
    """Result of strategy execution"""
    strategy_id: str
    challenge_id: str
    strategy_name: str
    execution_started_at: datetime
    execution_completed_at: Optional[datetime] = None
    success: bool
    votes_cast: int = 0
    error_message: Optional[str] = None
    result_data: Optional[Dict[str, Any]] = None


class StrategyStatusUpdate(BaseModel):
    """WebSocket notification for strategy status updates"""
    strategy_id: str
    profile_id: str
    challenge_id: str
    old_status: str
    new_status: str
    timestamp: datetime
    execution_result: Optional[StrategyExecutionResult] = None