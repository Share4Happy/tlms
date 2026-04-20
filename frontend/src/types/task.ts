/**
 * Task types matching backend models
 */

export type TaskType = 'core' | 'bounty';
export type TaskScope = 'mandatory' | 'opt_in' | 'private';
export type TaskDifficulty = 'easy' | 'medium' | 'hard' | 'expert';
export type TaskStatus = 'locked' | 'available' | 'in_progress' | 'submitted' | 'approved' | 'rejected' | 'completed';

export interface Task {
  id: string;
  title: string;
  description: string;
  type: TaskType;
  scope: TaskScope;
  max_participants?: number | null;
  assignee_ids?: string[];
  difficulty: TaskDifficulty;
  min_level_required: number;
  prerequisite_task_ids: string[];
  xp_reward: number;
  skill_tags: string[];
  instructions?: string | null;
  reference_links: string[];
  is_active: boolean;
  order_index: number;
  created_at: string;
  updated_at: string;
  creator_id?: string;
  creator_name?: string | null;
}

export interface UserTask {
  id: string;
  user_id: string;
  user_email?: string | null;
  user_full_name?: string | null;
  task_id: string;
  task: Task;
  status: TaskStatus;
  proof_link?: string | null;
  submission_notes?: string | null;
  submitted_at?: string | null;
  reviewer_id?: string | null;
  mentor_comment?: string | null;
  reviewed_at?: string | null;
  xp_earned: number;
  started_at?: string | null;
  completed_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface TaskListResponse {
  tasks: Task[];
  total: number;
  page: number;
  page_size: number;
}

export interface UserTaskListResponse {
  tasks: UserTask[];
  total: number;
  completed_count: number;
  pending_count: number;
  in_progress_count: number;
}

export interface TaskStatsResponse {
  total_tasks: number;
  core_tasks: number;
  bounty_tasks: number;
  active_tasks: number;
  total_xp_available: number;
}

export interface TaskStartRequest {
  task_id: string;
}

export interface TaskSubmitRequest {
  proof_link?: string;
  submission_notes?: string;
}

export interface TaskReviewRequest {
  status: 'approved' | 'rejected';
  mentor_comment?: string;
}

export interface TaskParticipant {
  id: string;
  email: string;
  full_name: string | null;
  avatar_url: string | null;
  role: string;
  level: number;
  current_xp: number;
  task_status: TaskStatus;
  started_at: string | null;
  submitted_at: string | null;
  completed_at: string | null;
  proof_link: string | null;
  mentor_comment: string | null;
  xp_earned: number;
}

export interface TaskDetailResponse {
  id: string;
  title: string;
  description: string;
  type: TaskType;
  scope: TaskScope;
  difficulty: TaskDifficulty;
  min_level_required: number;
  xp_reward: number;
  skill_tags: string[];
  is_active: boolean;
  max_participants: number | null;
  assignee_ids: string[];
  created_at: string;
  updated_at: string;
  total_participants: number;
  in_progress_count: number;
  submitted_count: number;
  completed_count: number;
  rejected_count: number;
  participants: TaskParticipant[];
}
