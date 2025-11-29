"""
Turbo system schemas for mobile app turbo management
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime
import re


class TurboExecutionRequest(BaseModel):
    """Request to execute turbo for a challenge"""
    challenge_id: str = Field(..., description="GuruShots challenge ID")
    challenge_title: Optional[str] = Field(None, description="Challenge title for display")
    challenge_time_left: Optional[str] = Field(None, description="Time left in challenge")
    algorithm: Optional[str] = Field(None, description="Override turbo algorithm (hybrid, position_aware, etc.)")
    
    @validator('challenge_id')
    def validate_challenge_id(cls, v):
        if not v or not v.strip():
            raise ValueError('Challenge ID cannot be empty')
        return v.strip()


class TurboExecutionResponse(BaseModel):
    """Response after turbo execution"""
    turbo_id: str
    profile_id: str
    challenge_id: str
    challenge_title: Optional[str]
    algorithm_used: str
    execution_started_at: datetime
    execution_completed_at: Optional[datetime] = None
    status: str  # 'running', 'completed', 'failed'
    success: bool = False
    pairs_processed: int = 0
    successful_pairs: int = 0
    failed_pairs: int = 0
    error_message: Optional[str] = None
    result_data: Optional[Dict[str, Any]] = None


class TurboStatusResponse(BaseModel):
    """Current turbo status for a challenge"""
    turbo_id: Optional[str] = None
    profile_id: str
    challenge_id: str
    status: str  # 'none', 'running', 'completed', 'failed'
    algorithm_used: Optional[str] = None
    execution_started_at: Optional[datetime] = None
    execution_completed_at: Optional[datetime] = None
    pairs_processed: int = 0
    successful_pairs: int = 0
    failed_pairs: int = 0
    success: bool = False


class TurboHistoryEntry(BaseModel):
    """Single turbo history entry"""
    turbo_id: str
    profile_id: str
    challenge_id: str
    challenge_title: str
    timestamp: datetime
    time_left: str
    algorithm: str
    strategy_description: str
    success: bool
    pairs_processed: int
    successful_pairs: int
    photo_pairs: List[Dict[str, Any]] = Field(default_factory=list)
    execution_duration: Optional[float] = None  # seconds
    boost: Optional[str] = None  # Boost status (e.g., "active", "inactive", "used")


class TurboHistoryResponse(BaseModel):
    """List of turbo history entries"""
    entries: List[TurboHistoryEntry]
    total_count: int
    success_count: int
    failed_count: int
    average_success_rate: float = 0.0


class TurboPairComparison(BaseModel):
    """Single turbo pair comparison data"""
    pair_number: int
    first_photo_id: str
    second_photo_id: str
    first_photo_data: Optional[Dict[str, Any]] = None
    second_photo_data: Optional[Dict[str, Any]] = None
    algorithm_choice: str  # ID of photo chosen by algorithm
    actual_winner: Optional[str] = None  # ID of actual winner from API
    first_score: Optional[float] = None  # Percentage score
    second_score: Optional[float] = None  # Percentage score
    success: bool = False
    is_retry: bool = False
    strategy_description: Optional[str] = None


class TurboAlgorithmConfig(BaseModel):
    """Turbo algorithm configuration"""
    algorithm_name: str = Field(..., description="Algorithm name (hybrid, position_aware, etc.)")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Algorithm-specific parameters")
    
    @validator('algorithm_name')
    def validate_algorithm_name(cls, v):
        valid_algorithms = [
            'hybrid', 'position_aware', 'adaptive_time', 'bruno_custom_refined',
            'ratio_low', 'votes_high', 'random'
        ]
        if v not in valid_algorithms:
            raise ValueError(f'Algorithm must be one of: {valid_algorithms}')
        return v


class TurboSettingsResponse(BaseModel):
    """Profile turbo settings"""
    profile_id: str
    algorithm: str
    auto_optimize_enabled: bool
    history_enabled: bool
    algorithm_config: Optional[TurboAlgorithmConfig] = None
    statistics: Dict[str, Any] = Field(default_factory=dict)


class TurboSettingsUpdateRequest(BaseModel):
    """Request to update turbo settings"""
    algorithm: Optional[str] = Field(None, description="Change algorithm")
    auto_optimize_enabled: Optional[bool] = Field(None, description="Enable/disable auto optimization")
    history_enabled: Optional[bool] = Field(None, description="Enable/disable history tracking")
    algorithm_config: Optional[TurboAlgorithmConfig] = Field(None, description="Algorithm configuration")
    
    @validator('algorithm')
    def validate_algorithm(cls, v):
        if v is not None:
            valid_algorithms = [
                'hybrid', 'position_aware', 'adaptive_time', 'bruno_custom_refined',
                'ratio_low', 'votes_high', 'random'
            ]
            if v not in valid_algorithms:
                raise ValueError(f'Algorithm must be one of: {valid_algorithms}')
        return v


class TurboStatisticsResponse(BaseModel):
    """Turbo performance statistics"""
    profile_id: str
    total_turbos: int = 0
    successful_turbos: int = 0
    failed_turbos: int = 0
    success_rate: float = 0.0
    average_pairs_processed: float = 0.0
    algorithm_performance: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    recent_performance: List[Dict[str, Any]] = Field(default_factory=list)
    trends: Dict[str, Any] = Field(default_factory=dict)


class AvailableAlgorithmsResponse(BaseModel):
    """List of available turbo algorithms"""
    algorithms: List[Dict[str, str]]  # [{"name": "hybrid", "description": "Hybrid ensemble algorithm"}, ...]


class TurboLogEntry(BaseModel):
    """Real-time turbo log entry for WebSocket"""
    turbo_id: str
    profile_id: str
    challenge_id: str
    timestamp: datetime
    level: str  # 'info', 'success', 'error', 'warning'
    message: str
    pair_number: Optional[int] = None
    data: Optional[Dict[str, Any]] = None


class TurboWebSocketUpdate(BaseModel):
    """WebSocket update for turbo execution"""
    turbo_id: str
    profile_id: str
    challenge_id: str
    update_type: str  # 'status', 'pair_result', 'log', 'completed'
    timestamp: datetime
    data: Dict[str, Any]