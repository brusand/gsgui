"""
Profile schemas for mobile app registration and management
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime


class ProfileRegisterRequest(BaseModel):
    """Request to register/connect a profile"""
    profile_name: str = Field(..., min_length=1, max_length=50, description="Profile name")
    gs_token: Optional[str] = Field(None, description="GuruShots token from cookies (optional if profile exists)")
    
    @validator('profile_name')
    def validate_profile_name(cls, v):
        # Nettoyer le nom de profil
        v = v.strip()
        if not v:
            raise ValueError('Profile name cannot be empty')
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('Profile name can only contain letters, numbers, underscores and hyphens')
        return v
    
    @validator('gs_token')
    def validate_gs_token(cls, v):
        if v is not None:
            v = v.strip()
            if len(v) < 10:  # Token GuruShots sont longs
                raise ValueError('gs_token seems too short')
        return v


class ProfileRegisterResponse(BaseModel):
    """Response after profile registration"""
    profile_id: str
    profile_name: str
    status: str  # 'existing', 'created', 'updated'
    message: str
    has_valid_token: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ProfileInfoResponse(BaseModel):
    """Detailed profile information"""
    profile_id: str
    profile_name: str
    has_valid_token: bool
    turbo_algorithm: str
    auto_optimize_turbo: bool
    turbo_history_enabled: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_activity: Optional[datetime] = None
    
    # Statistiques
    total_strategies: int = 0
    active_strategies: int = 0
    total_turbos: int = 0


class ProfileListResponse(BaseModel):
    """List of all profiles"""
    profiles: List[ProfileInfoResponse]
    total_count: int


class ProfileUpdateRequest(BaseModel):
    """Request to update profile settings"""
    turbo_algorithm: Optional[str] = Field(None, description="Turbo algorithm configuration")
    auto_optimize_turbo: Optional[bool] = Field(None, description="Auto optimization enabled")
    turbo_history_enabled: Optional[bool] = Field(None, description="History tracking enabled")
    gs_token: Optional[str] = Field(None, description="Update GuruShots token")


class ProfileValidationRequest(BaseModel):
    """Request to validate a gs_token"""
    gs_token: str = Field(..., description="GuruShots token to validate")


class ProfileValidationResponse(BaseModel):
    """Response for token validation"""
    is_valid: bool
    user_info: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    validation_timestamp: datetime


class ProfileStatsResponse(BaseModel):
    """Profile statistics"""
    profile_id: str
    strategies: Dict[str, int] = Field(default_factory=dict)  # {'pending': 5, 'completed': 10}
    turbos: Dict[str, int] = Field(default_factory=dict)      # {'total': 100, 'success': 75}
    activity: Dict[str, Any] = Field(default_factory=dict)    # Recent activity
    performance: Dict[str, float] = Field(default_factory=dict)  # Success rates


class ErrorResponse(BaseModel):
    """Standard error response"""
    error: str
    message: str
    timestamp: datetime
    details: Optional[Dict[str, Any]] = None