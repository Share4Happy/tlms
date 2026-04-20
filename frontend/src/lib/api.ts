/**
 * API Client for TLMS Backend
 */
import axios, { AxiosInstance, AxiosError } from 'axios';
import Cookies from 'js-cookie';
import { 
  AuthResponse, 
  LoginRequest, 
  RegisterRequest, 
  User, 
  UserListResponse, 
  UserStatsResponse, 
  UserRole, 
  UserStatus, 
  ApiError 
} from '@/types';
import {
  Task,
  UserTask,
  TaskListResponse,
  UserTaskListResponse,
  TaskStatsResponse,
  TaskDetailResponse,
  TaskStartRequest,
  TaskSubmitRequest,
  TaskReviewRequest,
  TaskType
} from '@/types/task';
import {
  LeaderboardResponse,
  UserRankInfo,
  LeaderboardStats
} from '@/types/leaderboard';
import {
  ProfileResponse,
  ProfileEvidence,
  ProfileEvidenceCreate,
  ProfileEvidenceUpdate,
  ProfileStats,
  AutoScheduleRequest,
  AutoScheduleResult
} from '@/types/profile';
import { ForceSyncAllUsersResponse } from '@/types/schedule';

const API_URL = process.env.NEXT_PUBLIC_API_URL || '/api';

class ApiClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: `${API_URL}/v1`,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Add auth token to requests
    this.client.interceptors.request.use((config) => {
      const token = Cookies.get('accessToken');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    });

    // Handle token refresh on 401
    this.client.interceptors.response.use(
      (response) => response,
      async (error: AxiosError<ApiError>) => {
        const originalRequest = error.config as any;
        const requestUrl = originalRequest?.url || '';
        const isAuthEndpoint =
          requestUrl.includes('/auth/login') ||
          requestUrl.includes('/auth/register') ||
          requestUrl.includes('/auth/refresh');

        if (
          error.response?.status === 401 &&
          originalRequest &&
          !isAuthEndpoint &&
          !originalRequest._retry
        ) {
          originalRequest._retry = true;
          const refreshToken = Cookies.get('refreshToken');
          
          if (refreshToken) {
            try {
              const response = await axios.post(`${API_URL}/v1/auth/refresh`, {
                refreshToken,
              });
              
              const { accessToken } = response.data;
              Cookies.set('accessToken', accessToken, { expires: 1 });
              
              originalRequest.headers.Authorization = `Bearer ${accessToken}`;
              return this.client(originalRequest);
            } catch (refreshError) {
              // Refresh failed, clear tokens
              this.clearTokens();
              if (typeof window !== 'undefined' && window.location.pathname !== '/login') {
                window.location.href = '/login';
              }
            }
          } else {
            this.clearTokens();
            if (typeof window !== 'undefined' && window.location.pathname !== '/login') {
              window.location.href = '/login';
            }
          }
        }
        
        return Promise.reject(error);
      }
    );
  }

  private setTokens(accessToken: string, refreshToken: string) {
    Cookies.set('accessToken', accessToken, { expires: 1 }); // 1 day
    Cookies.set('refreshToken', refreshToken, { expires: 7 }); // 7 days
  }

  private clearTokens() {
    Cookies.remove('accessToken');
    Cookies.remove('refreshToken');
  }

  async login(credentials: LoginRequest): Promise<AuthResponse> {
    const response = await this.client.post<AuthResponse>('/auth/login', credentials);
    const { tokens } = response.data;
    this.setTokens(tokens.accessToken, tokens.refreshToken);
    return response.data;
  }

  async register(data: RegisterRequest): Promise<{ message: string; success: boolean }> {
    const response = await this.client.post('/auth/register', data);
    return response.data;
  }

  async logout(): Promise<void> {
    try {
      await this.client.post('/auth/logout');
    } finally {
      this.clearTokens();
    }
  }

  async refreshToken(): Promise<string> {
    const refreshToken = Cookies.get('refreshToken');
    if (!refreshToken) {
      throw new Error('No refresh token');
    }
    
    const response = await this.client.post('/auth/refresh', { refreshToken });
    const { accessToken } = response.data;
    Cookies.set('accessToken', accessToken, { expires: 1 });
    return accessToken;
  }

  isAuthenticated(): boolean {
    return !!Cookies.get('accessToken');
  }

  // ============ User Management (Admin) ============
  
  async getMe(): Promise<User> {
    const response = await this.client.get<User>('/users/me');
    return response.data;
  }

  async checkAdminExists(): Promise<boolean> {
    const response = await this.client.get<{ has_admin: boolean }>('/users/check-admin-exists');
    return response.data.has_admin;
  }

  async listUsers(params?: {
    page?: number;
    page_size?: number;
    role?: UserRole;
    status?: UserStatus;
    search?: string;
  }): Promise<UserListResponse> {
    const response = await this.client.get<UserListResponse>('/users', { params });
    return response.data;
  }

  async getUser(userId: string): Promise<User> {
    const response = await this.client.get<User>(`/users/${userId}`);
    return response.data;
  }

  async updateUserRoles(userId: string, roles: UserRole[]): Promise<User> {
    const response = await this.client.patch<User>(`/users/${userId}/roles`, { roles });
    return response.data;
  }

  async updateUserStatus(userId: string, status: UserStatus): Promise<User> {
    const response = await this.client.patch<User>(`/users/${userId}/status`, { status });
    return response.data;
  }

  async setFirstAdmin(): Promise<User> {
    const response = await this.client.post<User>('/users/set-first-admin');
    return response.data;
  }

  async getUserStatsByRole(): Promise<UserStatsResponse> {
    const response = await this.client.get<UserStatsResponse>('/users/stats/by-role');
    return response.data;
  }

  // ============ Task Management ============

  // Tasks (all users)
  async listTasks(params?: {
    task_type?: TaskType;
    is_active?: boolean;
    page?: number;
    page_size?: number;
  }): Promise<TaskListResponse> {
    const response = await this.client.get<TaskListResponse>('/tasks', { params });
    return response.data;
  }

  async getTask(taskId: string): Promise<Task> {
    const response = await this.client.get<Task>(`/tasks/${taskId}`);
    return response.data;
  }

  async getTaskStats(): Promise<TaskStatsResponse> {
    const response = await this.client.get<TaskStatsResponse>('/tasks/stats');
    return response.data;
  }

  // User tasks
  async getAvailableTasks(): Promise<TaskListResponse> {
    const response = await this.client.get<TaskListResponse>('/tasks/available/me');
    return response.data;
  }

  async getMyTasks(status?: string): Promise<UserTaskListResponse> {
    const params = status ? { status } : {};
    const response = await this.client.get<UserTaskListResponse>('/tasks/my-tasks', { params });
    return response.data;
  }

  async getUserTasks(userId: string, status?: string): Promise<UserTaskListResponse> {
    const params = status ? { status } : {};
    const response = await this.client.get<UserTaskListResponse>(`/tasks/user/${userId}`, { params });
    return response.data;
  }

  async getUserStats(userId: string, weekStart?: string): Promise<any> {
    const params = weekStart ? { week_start: weekStart } : {};
    const response = await this.client.get(`/tasks/user-stats/${userId}`, { params });
    return response.data;
  }

  async startTask(data: TaskStartRequest): Promise<UserTask> {
    const response = await this.client.post<UserTask>('/tasks/start', data);
    return response.data;
  }

  async submitTask(userTaskId: string, data: TaskSubmitRequest): Promise<UserTask> {
    const response = await this.client.post<UserTask>(`/tasks/submit/${userTaskId}`, data);
    return response.data;
  }

  // Mentor
  async getPendingReviews(): Promise<UserTaskListResponse> {
    const response = await this.client.get<UserTaskListResponse>('/tasks/pending-reviews');
    return response.data;
  }

  async reviewTask(userTaskId: string, data: TaskReviewRequest): Promise<UserTask> {
    const response = await this.client.post<UserTask>(`/tasks/review/${userTaskId}`, data);
    return response.data;
  }

  // Admin - Create/Update/Delete tasks
  async createTask(data: any): Promise<Task> {
    const response = await this.client.post<Task>('/tasks', data);
    return response.data;
  }

  async updateTask(taskId: string, data: any): Promise<Task> {
    const response = await this.client.patch<Task>(`/tasks/${taskId}`, data);
    return response.data;
  }

  async deleteTask(taskId: string): Promise<void> {
    await this.client.delete(`/tasks/${taskId}`);
  }

  async getTaskDetails(taskId: string): Promise<TaskDetailResponse> {
    const response = await this.client.get<TaskDetailResponse>(`/tasks/${taskId}/details`);
    return response.data;
  }

  // ============ Leaderboard ============

  async getLeaderboard(params?: {
    role?: string;
    limit?: number;
  }): Promise<LeaderboardResponse> {
    const response = await this.client.get<LeaderboardResponse>('/leaderboard', { params });
    return response.data;
  }

  async getMyRank(): Promise<UserRankInfo> {
    const response = await this.client.get<UserRankInfo>('/leaderboard/my-rank');
    return response.data;
  }

  async getLeaderboardStats(): Promise<LeaderboardStats> {
    const response = await this.client.get<LeaderboardStats>('/leaderboard/stats');
    return response.data;
  }

  async getTopPerformers(limit: number = 10): Promise<any> {
    const response = await this.client.get(`/leaderboard/top/${limit}`);
    return response.data;
  }

  // ============ Schedule & Attendance ============

  async getWeekSchedules(weekStart: string): Promise<any> {
    const response = await this.client.get(`/schedules/week/${weekStart}`);
    return response.data;
  }

  async syncStudentSchedule(weekStart: string, force: boolean = false): Promise<any> {
    const response = await this.client.post(`/schedules/week/${weekStart}/sync`, null, {
      params: { force },
    });
    return response.data;
  }

  async forceSyncAllUsersSchedules(weekStart?: string): Promise<ForceSyncAllUsersResponse> {
    const payload = weekStart ? { week_start: weekStart } : {};
    const response = await this.client.post<ForceSyncAllUsersResponse>(
      '/schedules/admin/force-sync-all-users',
      payload
    );
    return response.data;
  }

  async getUsers(params?: any): Promise<any> {
    const response = await this.client.get('/users', { params });
    return response.data;
  }

  async getUserById(userId: string): Promise<User> {
    const response = await this.client.get<User>(`/users/${userId}`);
    return response.data;
  }

  async updateStudentId(studentId: string): Promise<User> {
    const response = await this.client.put<User>('/users/me/student-id', { student_id: studentId });
    return response.data;
  }

  async getMySchedules(params?: {
    start_date?: string;
    end_date?: string;
    include_cancelled?: boolean;
  }): Promise<any> {
    const response = await this.client.get('/schedules/my', { params });
    return response.data;
  }

  async registerWeekSchedules(data: any): Promise<any> {
    const response = await this.client.post('/schedules/week', data);
    return response.data;
  }

  async cancelSchedule(scheduleId: string, reason: string): Promise<any> {
    const response = await this.client.patch(`/schedules/${scheduleId}/cancel`, {
      reason
    });
    return response.data;
  }

  async checkIn(data: any): Promise<any> {
    const response = await this.client.post('/schedules/check-in', data);
    return response.data;
  }

  async checkOut(attendanceId: string, data: any): Promise<any> {
    const response = await this.client.post(`/schedules/check-out/${attendanceId}`, data);
    return response.data;
  }

  async getMyAttendances(params?: {
    start_date?: string;
    end_date?: string;
  }): Promise<any> {
    const response = await this.client.get('/schedules/attendance/my', { params });
    return response.data;
  }

  async getAttendanceStats(params?: {
    start_date?: string;
    end_date?: string;
  }): Promise<any> {
    const response = await this.client.get('/schedules/attendance/stats', { params });
    return response.data;
  }

  // ============================================
  // Manager - View multiple users schedules
  // ============================================

  async getUsersSchedulesForManager(weekStart: string, userIds: string[]): Promise<any> {
    const response = await this.client.get('/schedules/manager/users-schedules', {
      params: {
        week_start: weekStart,
        user_ids: userIds.join(',')
      }
    });
    return response.data;
  }

  // ============================================
  // Profile APIs
  // ============================================

  async getMyProfile(): Promise<ProfileResponse> {
    const response = await this.client.get<ProfileResponse>('/profile/me');
    return response.data;
  }

  async getProfileStats(): Promise<ProfileStats> {
    const response = await this.client.get<ProfileStats>('/profile/stats');
    return response.data;
  }

  async getUserProfile(userId: string): Promise<ProfileResponse> {
    const response = await this.client.get<ProfileResponse>(`/profile/user/${userId}`);
    return response.data;
  }

  async createEvidence(data: ProfileEvidenceCreate): Promise<ProfileEvidence> {
    const response = await this.client.post<ProfileEvidence>('/profile/evidence', data);
    return response.data;
  }

  async getEvidence(includePending: boolean = true): Promise<ProfileEvidence[]> {
    const response = await this.client.get<ProfileEvidence[]>('/profile/evidence', {
      params: { include_pending: includePending }
    });
    return response.data;
  }

  async updateEvidence(evidenceId: string, data: ProfileEvidenceUpdate): Promise<ProfileEvidence> {
    const response = await this.client.patch<ProfileEvidence>(`/profile/evidence/${evidenceId}`, data);
    return response.data;
  }

  async deleteEvidence(evidenceId: string): Promise<void> {
    await this.client.delete(`/profile/evidence/${evidenceId}`);
  }

  async verifyEvidence(evidenceId: string, data: any): Promise<ProfileEvidence> {
    const response = await this.client.post<ProfileEvidence>(`/profile/evidence/${evidenceId}/verify`, data);
    return response.data;
  }

  async autoSchedule(request: AutoScheduleRequest): Promise<AutoScheduleResult> {
    const response = await this.client.post<AutoScheduleResult>('/profile/auto-schedule', request);
    return response.data;
  }
}

export const apiClient = new ApiClient();
