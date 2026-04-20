"""
Auth Schemas - Pydantic models for request/response validation
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from app.models.user import UserRole, UserStatus


# ============================================
# Request Schemas
# ============================================

class LoginRequest(BaseModel):
    """Login request body - forwarded to S4H Auth"""
    email: EmailStr
    password: str = Field(..., min_length=1)
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "your_password"
            }
        }


class RegisterRequest(BaseModel):
    """Register request body - forwarded to S4H Auth"""
    email: EmailStr
    password: str = Field(..., min_length=6)
    firstName: str = Field(..., min_length=1, max_length=100)
    lastName: str = Field(..., min_length=1, max_length=100)
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "newuser@example.com",
                "password": "secure_password",
                "firstName": "Nguyen",
                "lastName": "Van A"
            }
        }


class RefreshTokenRequest(BaseModel):
    """Refresh token request body"""
    refreshToken: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "refreshToken": "your_refresh_token_here"
            }
        }


# ============================================
# Response Schemas
# ============================================

class TokenResponse(BaseModel):
    """Token response from S4H Auth - returned to client"""
    accessToken: str
    refreshToken: str


class RefreshedTokenResponse(BaseModel):
    """Refreshed token response"""
    accessToken: str


class S4HUserInfo(BaseModel):
    """User info returned from S4H /users/me endpoint"""
    id: str
    email: EmailStr
    phone: Optional[str] = None  # Phone number from S4H
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    role: Optional[str] = None
    studentCode: Optional[str] = None  # Student code from S4H if available


class UserResponse(BaseModel):
    """Local user response for TLMS"""
    id: UUID
    s4h_user_id: str
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: str
    roles: List[str]
    primary_role: str
    status: UserStatus
    current_xp: int
    discipline_score: float
    level: int
    core_task_progress: float
    is_ready_to_promote: bool
    created_at: datetime
    last_login_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class AuthenticatedUserResponse(BaseModel):
    """Response after successful authentication"""
    tokens: TokenResponse
    user: UserResponse


class MessageResponse(BaseModel):
    """Generic message response"""
    message: str
    success: bool = True


class ErrorResponse(BaseModel):
    """Error response"""
    error: str
    detail: Optional[str] = None
    success: bool = False
