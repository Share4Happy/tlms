"""
User Management Schemas
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr


class UserRolesUpdate(BaseModel):
    """Schema for updating user roles - Admin only"""
    roles: List[str]  # ['candidate', 'member', 'mentor', 'admin']


class UserStatusUpdate(BaseModel):
    """Schema for updating user status - Admin only"""
    status: str  # active, inactive, suspended


class UserResponse(BaseModel):
    """Public user information"""
    id: str  # UUID as string
    s4h_user_id: str
    student_id: Optional[str] = None
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: Optional[str] = None
    roles: List[str]  # Array of roles
    primary_role: str  # Highest priority role for display
    status: str
    current_xp: int
    level: int
    discipline_score: float
    core_task_progress: float
    is_ready_to_promote: bool
    created_at: datetime
    last_login_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    """Paginated user list"""
    users: List[UserResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class UserRoleChangeLog(BaseModel):
    """Log entry for role change"""
    user_id: int
    old_role: str
    new_role: str
    changed_by_id: int
    changed_at: datetime
    reason: Optional[str] = None
