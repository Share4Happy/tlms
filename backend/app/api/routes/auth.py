"""
Authentication Routes
Implements the auth endpoints using S4H Auth Service (Proxy Pattern)

Endpoints:
- POST /auth/login - Login through S4H Auth
- POST /auth/register - Register through S4H Auth  
- POST /auth/refresh - Refresh token through S4H Auth
- POST /auth/logout - Logout (client-side token removal)
- GET /auth/me - Get current user info
"""
import logging
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.api.deps import get_current_user
from app.services.s4h_auth import s4h_auth_service
from app.services.user import user_service
from app.models.user import User, UserRole
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    RefreshTokenRequest,
    TokenResponse,
    RefreshedTokenResponse,
    UserResponse,
    AuthenticatedUserResponse,
    MessageResponse
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/login",
    response_model=AuthenticatedUserResponse,
    summary="Đăng nhập",
    description="""
    Đăng nhập vào hệ thống TLMS.
    
    **Quy trình (Proxy Authentication):**
    1. Nhận email/password từ client
    2. Forward đến S4H Auth Service để xác thực
    3. Nếu thành công: Trả về JWT tokens và thông tin user local
    4. Nếu thất bại: Trả về lỗi "Sai tài khoản hoặc mật khẩu"
    
    **Lưu ý:** Password không được lưu trữ trong hệ thống này.
    """
)
async def login(
    credentials: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Login Flow (oauth.md section 4.1):
    1. Client sends email/password to Python Backend
    2. Python Backend forwards to S4H /auth/login
    3. If 200: Return JWT Token
    4. If 400/401: Return error
    
    IMPORTANT: Password is NEVER stored (Zero Trust Password policy)
    """
    # Forward login to S4H Auth
    tokens = await s4h_auth_service.login(credentials)
    
    # Get user info from S4H with the new token
    s4h_user_info = await s4h_auth_service.get_user_info(tokens.accessToken)
    
    # Lazy Sync: Get or create local user
    user = await user_service.get_or_create_user(db, s4h_user_info)
    
    # Update last login
    await user_service.update_user_login(db, user)
    
    logger.info(f"User logged in: {user.email}")
    
    # Calculate display level
    display_level = user.level
    if user.primary_role in [UserRole.MENTOR.value, UserRole.ADMIN.value]:
        display_level = 99

    return AuthenticatedUserResponse(
        tokens=tokens,
        user=UserResponse(
            id=str(user.id),
            s4h_user_id=user.s4h_user_id,
            email=user.email,
            student_id=user.student_id,
            first_name=user.first_name,
            last_name=user.last_name,
            full_name=user.full_name,
            roles=user.roles or ['candidate'],
            primary_role=user.primary_role,
            status=user.status.value if hasattr(user.status, 'value') else user.status,
            current_xp=user.current_xp,
            discipline_score=user.discipline_score,
            level=display_level,
            core_task_progress=user.core_task_progress,
            is_ready_to_promote=user.is_ready_to_promote,
            created_at=user.created_at,
            last_login_at=user.last_login_at
        )
    )


@router.post(
    "/register",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Đăng ký tài khoản mới",
    description="""
    Đăng ký tài khoản mới trong hệ thống.
    
    **Quy trình:**
    1. Nhận thông tin đăng ký từ client
    2. Forward đến S4H Auth Service
    3. Nếu thành công: Trả về thông báo thành công
    4. Nếu thất bại: Trả về lỗi (email đã tồn tại, etc.)
    
    **Lưu ý:** 
    - Password không được lưu trong hệ thống TLMS
    - User local sẽ được tạo tự động khi đăng nhập lần đầu
    """
)
async def register(user_data: RegisterRequest):
    """
    Register new user through S4H Auth
    
    Note: Local user record is NOT created here.
    It will be created via Lazy Sync when user logs in.
    """
    await s4h_auth_service.register(user_data)
    
    logger.info(f"New user registered: {user_data.email}")
    
    return MessageResponse(
        message="Đăng ký thành công. Vui lòng đăng nhập để tiếp tục.",
        success=True
    )


@router.post(
    "/refresh",
    response_model=RefreshedTokenResponse,
    summary="Làm mới Access Token",
    description="""
    Làm mới access token bằng refresh token.
    
    **Sử dụng khi:**
    - Access token hết hạn (401 Unauthorized)
    - Client cần token mới mà không cần đăng nhập lại
    """
)
async def refresh_token(refresh_request: RefreshTokenRequest):
    """
    Refresh access token using refresh token
    Forward to S4H /auth/refresh
    """
    result = await s4h_auth_service.refresh_token(refresh_request)
    
    logger.info("Token refreshed successfully")
    
    return result


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Đăng xuất",
    description="""
    Đăng xuất khỏi hệ thống.
    
    **Lưu ý:** 
    - JWT tokens là stateless, server không lưu session
    - Client cần tự xóa tokens khỏi storage
    - Endpoint này chỉ để confirm và có thể dùng cho logging
    """
)
async def logout(current_user: User = Depends(get_current_user)):
    """
    Logout user
    
    Since JWT is stateless, actual logout happens client-side
    by removing the tokens from storage.
    
    This endpoint:
    1. Confirms valid token
    2. Logs the logout event
    3. Returns success message
    
    For better security, consider implementing token blacklist
    using Redis (mentioned in oauth.md section 6).
    """
    logger.info(f"User logged out: {current_user.email}")
    
    return MessageResponse(
        message="Đăng xuất thành công",
        success=True
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Lấy thông tin user hiện tại",
    description="""
    Lấy thông tin chi tiết của user đang đăng nhập.
    
    **Yêu cầu:** Bearer token trong header Authorization
    """
)
async def get_me(current_user: User = Depends(get_current_user)):
    """
    Get current authenticated user info
    This also validates the token is still valid
    """
    # Calculate display level
    display_level = current_user.level
    if current_user.primary_role in [UserRole.MENTOR.value, UserRole.ADMIN.value]:
        display_level = 99

    return UserResponse(
        id=str(current_user.id),
        s4h_user_id=current_user.s4h_user_id,
        email=current_user.email,
        student_id=current_user.student_id,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        full_name=current_user.full_name,
        roles=current_user.roles or ['candidate'],
        primary_role=current_user.primary_role,
        status=current_user.status.value if hasattr(current_user.status, 'value') else current_user.status,
        current_xp=current_user.current_xp,
        discipline_score=current_user.discipline_score,
        level=display_level,
        core_task_progress=current_user.core_task_progress,
        is_ready_to_promote=current_user.is_ready_to_promote,
        created_at=current_user.created_at,
        last_login_at=current_user.last_login_at
    )
