"""
Task Service - Business logic for task management
"""
import logging
from typing import List, Optional
from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from uuid import UUID
from datetime import datetime

from app.models.task import Task, UserTask, TaskType, TaskStatus, TaskScope
from app.models.user import User, UserRole
from app.schemas.task import TaskCreate, TaskUpdate
from app.core.exceptions import (
    NotFoundException,
    BadRequestException,
    ForbiddenException
)
from sqlalchemy import or_

logger = logging.getLogger(__name__)


class TaskService:
    """Service for managing tasks"""
    
    # ============================================
    # Task CRUD (Admin only)
    # ============================================
    
    async def create_task(
        self,
        db: AsyncSession,
        task_data: TaskCreate,
        creator: User
    ) -> Task:
        """Create a new task (Admin or Mentor)"""
        if not (creator.is_admin() or creator.is_mentor()):
            raise ForbiddenException("Only admins and mentors can create tasks")
        
        task = Task(
            title=task_data.title,
            description=task_data.description,
            type=task_data.type,
            scope=task_data.scope,
            difficulty=task_data.difficulty,
            min_level_required=task_data.min_level_required,
            prerequisite_task_ids=task_data.prerequisite_task_ids,
            xp_reward=task_data.xp_reward,
            skill_tags=task_data.skill_tags,
            instructions=task_data.instructions,
            reference_links=task_data.reference_links,
            is_active=task_data.is_active,
            order_index=task_data.order_index,
            max_participants=task_data.max_participants,
            assignee_ids=task_data.assignee_ids,
            creator_id=creator.id
        )
        
        db.add(task)
        await db.commit()
        await db.refresh(task)
        
        # Auto-assignment logic
        if task.scope == TaskScope.MANDATORY:
            # Assign to ALL Candidates and Members
            stmt = select(User).where(
                or_(
                   User.roles.contains([UserRole.CANDIDATE.value]),
                   User.roles.contains([UserRole.MEMBER.value])
                )
            )
            users = (await db.execute(stmt)).scalars().all()
            for u in users:
                # Check if already exists (paranoia check)
                stmt_check = select(UserTask).where(UserTask.user_id==u.id, UserTask.task_id==task.id)
                if not (await db.execute(stmt_check)).scalar_one_or_none():
                    user_task = UserTask(
                        user_id=u.id,
                        task_id=task.id,
                        status=TaskStatus.AVAILABLE
                    )
                    db.add(user_task)
            await db.commit()
            
        elif task.scope == TaskScope.PRIVATE:
            # Assign to specific IDs
            for uid_str in task.assignee_ids:
                try:
                    uid = UUID(uid_str)
                    user_task = UserTask(
                        user_id=uid,
                        task_id=task.id,
                        status=TaskStatus.AVAILABLE
                    )
                    db.add(user_task)
                except ValueError:
                    logger.warning(f"Invalid UUID in assignee_ids: {uid_str}")
            await db.commit()
        
        logger.info(f"Task created: {task.title} by {creator.email}")
        return task
    
    async def update_task(
        self,
        db: AsyncSession,
        task_id: UUID,
        task_data: TaskUpdate,
        updater: User
    ) -> Task:
        """Update a task (Admin only)"""
        if not updater.is_admin():
            raise ForbiddenException("Only admins can update tasks")
        
        task = await self.get_task_by_id(db, task_id)
        
        update_data = task_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(task, field, value)
        
        await db.commit()
        await db.refresh(task)
        
        logger.info(f"Task updated: {task.title} by {updater.email}")
        return task
    
    async def delete_task(
        self,
        db: AsyncSession,
        task_id: UUID,
        deleter: User
    ):
        """Delete a task (Admin or Mentor)"""
        if not (deleter.is_admin() or deleter.is_mentor()):
            raise ForbiddenException("Only admins and mentors can delete tasks")

        task = await self.get_task_by_id(db, task_id)

        await db.delete(task)
        await db.commit()

        logger.info(f"Task deleted: {task.title} by {deleter.email}")
    
    async def get_task_by_id(
        self,
        db: AsyncSession,
        task_id: UUID
    ) -> Task:
        """Get task by ID"""
        result = await db.execute(
            select(Task)
            .options(selectinload(Task.creator))
            .where(Task.id == task_id)
        )
        task = result.scalar_one_or_none()

        if not task:
            raise NotFoundException(f"Task not found: {task_id}")

        return task
    
    async def list_tasks(
        self,
        db: AsyncSession,
        task_type: Optional[TaskType] = None,
        is_active: Optional[bool] = None,
        page: int = 1,
        page_size: int = 50
    ) -> tuple[List[Task], int]:
        """List tasks with filtering and pagination"""
        query = select(Task).options(selectinload(Task.creator))

        # Filters
        if task_type:
            query = query.where(Task.type == task_type)
        if is_active is not None:
            query = query.where(Task.is_active == is_active)

        # Order by type (core first) and then order_index
        query = query.order_by(Task.type, Task.order_index, Task.created_at)

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar()

        # Pagination
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await db.execute(query)
        tasks = result.scalars().all()

        return list(tasks), total
    
    async def get_task_stats(self, db: AsyncSession) -> dict:
        """Get task statistics"""
        result = await db.execute(
            select(
                func.count(Task.id).label('total'),
                func.sum(func.cast(Task.type == TaskType.CORE, Integer)).label('core'),
                func.sum(func.cast(Task.type == TaskType.BOUNTY, Integer)).label('bounty'),
                func.sum(func.cast(Task.is_active == True, Integer)).label('active'),
                func.sum(Task.xp_reward).label('total_xp')
            )
        )
        stats = result.one()
        
        return {
            'total_tasks': stats.total or 0,
            'core_tasks': stats.core or 0,
            'bounty_tasks': stats.bounty or 0,
            'active_tasks': stats.active or 0,
            'total_xp_available': stats.total_xp or 0
        }
    
    # ============================================
    # User Task Management
    # ============================================
    
    async def get_user_available_tasks(
        self,
        db: AsyncSession,
        user: User
    ) -> List[Task]:
        """
        Get tasks available for user based on:
        - User's level
        - Prerequisites completion
        - Not already completed
        """
        # Get all active tasks
        result = await db.execute(
            select(Task)
            .where(Task.is_active == True)
            .where(Task.min_level_required <= user.level)
            .order_by(Task.type, Task.order_index)
        )
        all_tasks = result.scalars().all()
        
        # Get user's completed task IDs
        completed_result = await db.execute(
            select(UserTask.task_id)
            .where(UserTask.user_id == user.id)
            .where(UserTask.status == TaskStatus.COMPLETED)
        )
        completed_task_ids = {str(row[0]) for row in completed_result.all()}
        
        # Filter tasks based on prerequisites
        available_tasks = []
        for task in all_tasks:
            # Skip if already completed
            if str(task.id) in completed_task_ids:
                continue
            
            # Check prerequisites
            if task.prerequisite_task_ids:
                prerequisites_met = all(
                    prereq_id in completed_task_ids
                    for prereq_id in task.prerequisite_task_ids
                )
                if not prerequisites_met:
                    continue
            
            available_tasks.append(task)
        
        return available_tasks
    
    async def start_task(
        self,
        db: AsyncSession,
        user: User,
        task_id: UUID
    ) -> UserTask:
        """User starts/claims a task"""
        task = await self.get_task_by_id(db, task_id)
        
        # Check if task is active
        if not task.is_active:
            raise BadRequestException("This task is not active")
        
        # Check level requirement
        if user.level < task.min_level_required:
            raise ForbiddenException(
                f"Level {task.min_level_required} required. You are level {user.level}"
            )
        
        # Check if already exists
        result = await db.execute(
            select(UserTask)
            .where(UserTask.user_id == user.id)
            .where(UserTask.task_id == task_id)
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            if existing.status == TaskStatus.COMPLETED:
                raise BadRequestException("Task already completed")
            
            # If assigned/available, start it now
            if existing.status == TaskStatus.AVAILABLE:
                existing.status = TaskStatus.IN_PROGRESS
                existing.started_at = datetime.utcnow()
                await db.commit()
                await db.refresh(existing)
            
            # If exists (in progress or just updated), return it
            return existing
        
        # New Enrolment Logic based on Scope
        if task.scope == TaskScope.PRIVATE:
             # Private tasks must be pre-assigned
             raise ForbiddenException("This is a private task and you are not in the assignee list.")
        
        elif task.scope == TaskScope.OPT_IN and task.max_participants:
             # Check capacity
             count_stmt = select(func.count(UserTask.id)).where(UserTask.task_id == task_id)
             current_count = (await db.execute(count_stmt)).scalar() or 0
             
             if current_count >= task.max_participants:
                 raise BadRequestException("Task is full (Maximum participants reached)")

        # Check prerequisites
        if task.prerequisite_task_ids:
            completed_result = await db.execute(
                select(UserTask.task_id)
                .where(UserTask.user_id == user.id)
                .where(UserTask.status == TaskStatus.COMPLETED)
            )
            completed_ids = {str(row[0]) for row in completed_result.all()}
            
            prerequisites_met = all(
                prereq_id in completed_ids
                for prereq_id in task.prerequisite_task_ids
            )
            
            if not prerequisites_met:
                raise ForbiddenException("Prerequisites not met for this task")
        
        # Create user task
        user_task = UserTask(
            user_id=user.id,
            task_id=task_id,
            status=TaskStatus.IN_PROGRESS,
            started_at=datetime.utcnow()
        )
        
        db.add(user_task)
        await db.commit()
        await db.refresh(user_task)
        
        logger.info(f"Task started: {task.title} by {user.email}")
        return user_task
    
    async def submit_task(
        self,
        db: AsyncSession,
        user: User,
        user_task_id: UUID,
        proof_link: str,
        submission_notes: Optional[str] = None
    ) -> UserTask:
        """User submits task for review"""
        logger.info(f"Attempting to submit task {user_task_id} for user {user.id}")
        
        result = await db.execute(
            select(UserTask)
            .options(selectinload(UserTask.task))
            .where(UserTask.id == user_task_id)
            .where(UserTask.user_id == user.id)
        )
        user_task = result.scalar_one_or_none()

        if not user_task:
            logger.error(f"Task {user_task_id} not found for user {user.id}")
            # Log all user tasks for this user for debugging
            all_tasks_result = await db.execute(
                select(UserTask)
                .where(UserTask.user_id == user.id)
            )
            all_tasks = all_tasks_result.scalars().all()
            logger.error(f"User {user.id} has {len(all_tasks)} tasks: {[str(t.id) for t in all_tasks]}")
            raise NotFoundException("Task not found")

        logger.info(f"Found task: {user_task.id}, status: {user_task.status}")

        if user_task.status == TaskStatus.COMPLETED:
            raise BadRequestException("Task already completed")

        if user_task.status == TaskStatus.SUBMITTED:
            raise BadRequestException("Task already submitted, waiting for review")

        user_task.status = TaskStatus.SUBMITTED
        user_task.proof_link = proof_link
        user_task.submission_notes = submission_notes
        user_task.submitted_at = datetime.utcnow()

        await db.commit()
        await db.refresh(user_task)

        logger.info(f"Task submitted: {user_task.task.title} by {user.email}")
        return user_task
    
    async def review_task(
        self,
        db: AsyncSession,
        mentor: User,
        user_task_id: UUID,
        approved: bool,
        mentor_comment: Optional[str] = None
    ) -> UserTask:
        """Mentor reviews and approves/rejects task"""
        if not mentor.is_mentor() and not mentor.is_admin():
            raise ForbiddenException("Only mentors can review tasks")

        result = await db.execute(
            select(UserTask)
            .options(
                selectinload(UserTask.task),
                selectinload(UserTask.user)
            )
            .where(UserTask.id == user_task_id)
        )
        user_task = result.scalar_one_or_none()

        if not user_task:
            raise NotFoundException("Task submission not found")

        if user_task.status != TaskStatus.SUBMITTED:
            raise BadRequestException("Task is not in submitted status")

        if approved:
            user_task.status = TaskStatus.COMPLETED
            user_task.xp_earned = user_task.task.xp_reward
            user_task.completed_at = datetime.utcnow()

            # Check if user should get XP (not mentor/admin)
            user_roles = user_task.user.roles if user_task.user.roles else []
            should_get_xp = UserRole.MENTOR.value not in user_roles and UserRole.ADMIN.value not in user_roles

            if should_get_xp:
                user_task.user.current_xp += user_task.xp_earned
                user_task.user.level = user_task.user.calculate_level()
                logger.info(
                    f"Task approved: {user_task.task.title} for {user_task.user.email}. "
                    f"XP +{user_task.xp_earned} (Total: {user_task.user.current_xp}, Level: {user_task.user.level})"
                )
            else:
                logger.info(
                    f"Task approved: {user_task.task.title} for {user_task.user.email}. "
                    f"No XP for mentor/admin role"
                )
                user_task.xp_earned = 0  # No XP for mentors/admins

            # Update core task progress if it's a core task
            if user_task.task.type == TaskType.CORE:
                await self._update_core_task_progress(db, user_task.user)

        else:
            user_task.status = TaskStatus.REJECTED
            logger.info(f"Task rejected: {user_task.task.title} for {user_task.user.email}")

        user_task.reviewer_id = mentor.id
        user_task.mentor_comment = mentor_comment
        user_task.reviewed_at = datetime.utcnow()

        await db.commit()
        
        # Reload user_task with updated user data using explicit query
        result = await db.execute(
            select(UserTask)
            .options(selectinload(UserTask.user))
            .where(UserTask.id == user_task_id)
        )
        user_task = result.scalar_one_or_none()

        return user_task
    
    async def _update_core_task_progress(self, db: AsyncSession, user: User):
        """Update user's core task completion percentage"""
        # Count total core tasks
        total_result = await db.execute(
            select(func.count(Task.id))
            .where(Task.type == TaskType.CORE)
            .where(Task.is_active == True)
        )
        total_core = total_result.scalar() or 0
        
        if total_core == 0:
            user.core_task_progress = 0.0
            return
        
        # Count completed core tasks for this user
        completed_result = await db.execute(
            select(func.count(UserTask.id))
            .join(Task)
            .where(UserTask.user_id == user.id)
            .where(UserTask.status == TaskStatus.COMPLETED)
            .where(Task.type == TaskType.CORE)
        )
        completed_core = completed_result.scalar() or 0
        
        user.core_task_progress = (completed_core / total_core) * 100.0
        logger.info(f"Core task progress updated: {user.email} - {user.core_task_progress:.1f}%")
    
    async def get_user_tasks(
        self,
        db: AsyncSession,
        user: User,
        status: Optional[TaskStatus] = None
    ) -> tuple[List[UserTask], dict]:
        """Get user's task progress"""
        query = select(UserTask).options(
            selectinload(UserTask.task).selectinload(Task.creator)
        ).where(UserTask.user_id == user.id)

        if status:
            query = query.where(UserTask.status == status)

        query = query.order_by(UserTask.created_at.desc())

        result = await db.execute(query)
        user_tasks = result.scalars().all()
        
        # Get counts by status
        count_result = await db.execute(
            select(
                UserTask.status,
                func.count(UserTask.id)
            )
            .where(UserTask.user_id == user.id)
            .group_by(UserTask.status)
        )
        
        counts = {
            'total': len(user_tasks),
            'completed': 0,
            'in_progress': 0,
            'submitted': 0
        }
        
        for status_val, count in count_result.all():
            if status_val == TaskStatus.COMPLETED:
                counts['completed'] = count
            elif status_val == TaskStatus.IN_PROGRESS:
                counts['in_progress'] = count
            elif status_val == TaskStatus.SUBMITTED:
                counts['submitted'] = count
        
        return list(user_tasks), counts
    
    async def get_pending_reviews(
        self,
        db: AsyncSession,
        mentor: User
    ) -> List[UserTask]:
        """Get tasks pending review (for mentors)"""
        if not mentor.is_mentor() and not mentor.is_admin():
            raise ForbiddenException("Only mentors can view pending reviews")
        
        result = await db.execute(
            select(UserTask)
            .options(
                selectinload(UserTask.task),
                selectinload(UserTask.user)
            )
            .where(UserTask.status == TaskStatus.SUBMITTED)
            .order_by(UserTask.submitted_at)
        )

        return list(result.scalars().all())

    async def get_task_detail_with_participants(
        self,
        db: AsyncSession,
        task_id: UUID
    ) -> dict:
        """Get task details with participant statistics and list"""
        # Get task
        task = await self.get_task_by_id(db, task_id)
        
        # Get all user tasks for this task
        result = await db.execute(
            select(UserTask)
            .options(selectinload(UserTask.user))
            .where(UserTask.task_id == task_id)
            .order_by(
                # Sort by status priority: COMPLETED first, then by completion time
                case(
                    (UserTask.status == TaskStatus.COMPLETED, 1),
                    (UserTask.status == TaskStatus.SUBMITTED, 2),
                    (UserTask.status == TaskStatus.IN_PROGRESS, 3),
                    (UserTask.status == TaskStatus.REJECTED, 4),
                    else_=5
                ),
                UserTask.completed_at.asc().nullsfirst(),
                UserTask.started_at.asc().nullsfirst()
            )
        )
        user_tasks = result.scalars().all()
        
        # Count by status
        in_progress_count = sum(1 for ut in user_tasks if ut.status == TaskStatus.IN_PROGRESS)
        submitted_count = sum(1 for ut in user_tasks if ut.status == TaskStatus.SUBMITTED)
        completed_count = sum(1 for ut in user_tasks if ut.status == TaskStatus.COMPLETED)
        rejected_count = sum(1 for ut in user_tasks if ut.status == TaskStatus.REJECTED)
        
        # Build participants list
        participants = []
        for ut in user_tasks:
            user = ut.user
            if not user:
                continue  # Skip if user is deleted
            participants.append({
                'id': str(user.id),
                'email': user.email,
                'full_name': user.full_name,
                'avatar_url': None,  # User model doesn't have avatar_url
                'role': user.primary_role,
                'level': user.level,
                'current_xp': user.current_xp,
                'task_status': ut.status.value if hasattr(ut.status, 'value') else str(ut.status),
                'started_at': ut.started_at,
                'submitted_at': ut.submitted_at,
                'completed_at': ut.completed_at,
                'proof_link': ut.proof_link,
                'mentor_comment': ut.mentor_comment,
                'xp_earned': ut.xp_earned
            })
        
        return {
            'id': task.id,
            'title': task.title,
            'description': task.description,
            'type': task.type,
            'scope': task.scope,
            'difficulty': task.difficulty,
            'min_level_required': task.min_level_required,
            'xp_reward': task.xp_reward,
            'skill_tags': task.skill_tags,
            'is_active': task.is_active,
            'max_participants': task.max_participants,
            'assignee_ids': [str(aid) for aid in task.assignee_ids] if task.assignee_ids else [],
            'created_at': task.created_at,
            'updated_at': task.updated_at,
            'total_participants': len(user_tasks),
            'in_progress_count': in_progress_count,
            'submitted_count': submitted_count,
            'completed_count': completed_count,
            'rejected_count': rejected_count,
            'participants': participants
        }


task_service = TaskService()
