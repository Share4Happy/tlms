"""
Background Tasks Service - Automatic schedule synchronization
"""
import logging
import pytz
from datetime import date, timedelta
from typing import Optional, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import get_settings
from app.models.user import User
from app.services.schedule import schedule_service

logger = logging.getLogger(__name__)

settings = get_settings()

# Vietnam timezone (UTC+7)
VN_TIMEZONE = pytz.timezone('Asia/Ho_Chi_Minh')

# Global scheduler instance with Vietnam timezone
scheduler = AsyncIOScheduler(timezone=VN_TIMEZONE)


async def _sync_all_user_schedules_for_week(
    week_start: date,
    force_update: bool = True,
    source: str = "system"
) -> Dict[str, Any]:
    """Sync schedules for all users having student_id for a specific week."""
    logger.info(
        "Starting %s schedule sync for week %s...",
        source,
        week_start.isoformat()
    )

    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False
    )

    async_session = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False
    )

    try:
        # Get list of users to sync (using a separate session)
        async with async_session() as list_session:
            result = await list_session.execute(
                select(User).where(
                    User.student_id.isnot(None),
                    User.student_id != ""
                )
            )
            users_to_sync = result.scalars().all()

        total_users = len(users_to_sync)
        logger.info("Found %s users with student IDs to sync", total_users)

        if total_users == 0:
            return {
                "week_start": week_start.isoformat(),
                "total_users": 0,
                "success_count": 0,
                "error_count": 0,
                "failed_users": []
            }

        success_count = 0
        error_count = 0
        failed_users = []

        # Process each user in a separate session to avoid rollback issues
        for user in users_to_sync:
            # Create a new session for each user
            async with async_session() as db:
                try:
                    await schedule_service.sync_student_schedule(
                        db=db,
                        user=user,
                        week_start=week_start,
                        force_update=force_update
                    )
                    await db.commit()
                    success_count += 1
                except Exception as e:
                    error_count += 1
                    failed_users.append(
                        {
                            "user_id": str(user.id),
                            "email": user.email,
                            "student_id": user.student_id,
                            "error": str(e)
                        }
                    )
                    logger.error(
                        "Failed to sync schedule for %s (%s): %s",
                        user.email,
                        user.student_id,
                        str(e)
                    )
                    # Don't call rollback here - async with will handle it

        summary = {
            "week_start": week_start.isoformat(),
            "total_users": total_users,
            "success_count": success_count,
            "error_count": error_count,
            "failed_users": failed_users
        }

        logger.info(
            "Schedule sync completed for week %s: %s succeeded, %s failed",
            week_start.isoformat(),
            success_count,
            error_count
        )
        return summary
        
    finally:
        await engine.dispose()


async def sync_all_user_schedules():
    """
    Background job: Sync schedules for all users with student IDs
    Runs weekly on Monday at 00:00 (or configurable)
    """
    try:
        # Get the start of current week (Monday)
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        await _sync_all_user_schedules_for_week(
            week_start=week_start,
            force_update=True,
            source="automatic"
        )
    except Exception as e:
        logger.error(f"Critical error in background schedule sync: {str(e)}", exc_info=True)


async def force_sync_all_user_schedules(week_start: Optional[date] = None) -> Dict[str, Any]:
    """Manual admin operation to force sync all schedules for users with student_id."""
    effective_week_start = week_start
    if effective_week_start is None:
        today = date.today()
        effective_week_start = today - timedelta(days=today.weekday())

    return await _sync_all_user_schedules_for_week(
        week_start=effective_week_start,
        force_update=True,
        source="manual-admin"
    )


async def sync_next_week_schedules():
    """
    Background job: Sync schedules for next week
    Runs on Friday at 18:00 to prepare next week's schedules
    [DISABLED - Use weekly sync on Monday only]
    """
    pass


def start_scheduler():
    """
    Start the background scheduler
    Called during application startup
    """
    if scheduler.running:
        logger.warning("Scheduler is already running")
        return
    
    try:
        # Weekly sync: Every Monday at 00:00 (midnight)
        scheduler.add_job(
            sync_all_user_schedules,
            trigger=CronTrigger(day_of_week=0, hour=0, minute=0),  # Monday 00:00
            id="weekly_schedule_sync",
            name="Weekly schedule sync for all users",
            replace_existing=True,
            max_instances=1
        )
        
        scheduler.start()
        logger.info("✓ Background scheduler started successfully")
        logger.info("  - Weekly sync: Every Monday at 00:00 (Vietnam Time - UTC+7)")
        
    except Exception as e:
        logger.error(f"Failed to start scheduler: {str(e)}", exc_info=True)
        raise


def stop_scheduler():
    """
    Stop the background scheduler
    Called during application shutdown
    """
    if not scheduler.running:
        logger.warning("Scheduler is not running")
        return
    
    try:
        scheduler.shutdown(wait=False)
        logger.info("✓ Background scheduler stopped")
    except Exception as e:
        logger.error(f"Error stopping scheduler: {str(e)}")


def get_scheduler_status():
    """
    Get scheduler status and job information
    """
    return {
        "running": scheduler.running,
        "jobs": [
            {
                "id": job.id,
                "name": job.name,
                "trigger": str(job.trigger),
                "next_run_time": str(job.next_run_time) if job.next_run_time else None
            }
            for job in scheduler.get_jobs()
        ]
    }
