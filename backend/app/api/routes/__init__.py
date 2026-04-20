"""
API Routes package
"""
from fastapi import APIRouter
from app.api.routes import auth, users, tasks, leaderboard, schedules, profile, admin, webhook

# Main API router
api_router = APIRouter()

# Include auth routes
api_router.include_router(auth.router)

# Include user management routes (Admin)
api_router.include_router(users.router)

# Include admin operations routes
api_router.include_router(admin.router)

# Include task management routes
api_router.include_router(tasks.router)

# Include leaderboard routes
api_router.include_router(leaderboard.router)

# Include schedule and attendance routes
api_router.include_router(schedules.router)

# Include profile routes
api_router.include_router(profile.router)

# Include webhook routes (S4H check-in)
api_router.include_router(webhook.router)

# Future routes will be added here:
# api_router.include_router(skills.router)
