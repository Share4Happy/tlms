'use client';

import { useAuth } from '@/contexts/AuthContext';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { apiClient } from '@/lib/api';
import { Task, UserTask } from '@/types/task';
import Link from 'next/link';

const DIFFICULTY_COLORS: Record<string, string> = {
  easy: 'bg-emerald-100 text-emerald-700',
  medium: 'bg-amber-100 text-amber-700',
  hard: 'bg-orange-100 text-orange-700',
  expert: 'bg-red-100 text-red-700',
};

const STATUS_COLORS: Record<string, string> = {
  available: 'bg-slate-100 text-slate-700',
  in_progress: 'bg-blue-100 text-blue-700',
  submitted: 'bg-violet-100 text-violet-700',
  approved: 'bg-emerald-100 text-emerald-700',
  completed: 'bg-emerald-100 text-emerald-700',
  rejected: 'bg-red-100 text-red-700',
  locked: 'bg-slate-100 text-slate-500',
};

export default function CandidateDashboard() {
  const { user, isLoading } = useAuth();
  const router = useRouter();
  const [availableTasks, setAvailableTasks] = useState<Task[]>([]);
  const [myTasks, setMyTasks] = useState<UserTask[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'available' | 'my-tasks'>('available');

  useEffect(() => {
    if (!isLoading && !user) {
      router.push('/login');
      return;
    }

    if (user) {
      loadData();
    }
  }, [isLoading, user, router]);

  const loadData = async () => {
    try {
      setLoading(true);
      const [available, myTasksData] = await Promise.all([
        apiClient.getAvailableTasks(),
        apiClient.getMyTasks(),
      ]);
      setAvailableTasks(available.tasks);
      setMyTasks(myTasksData.tasks);
    } catch (error) {
      console.error('Failed to load tasks:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleStartTask = async (taskId: string) => {
    try {
      await apiClient.startTask({ task_id: taskId });
      await loadData();
      setActiveTab('my-tasks');
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Failed to start task');
    }
  };

  if (isLoading || !user) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="w-6 h-6 border-2 border-gray-300 border-t-[#1E90FF] rounded-full animate-spin"></div>
      </div>
    );
  }

  const inProgressCount = myTasks.filter(t => t.status === 'in_progress').length;
  const completedCount = myTasks.filter(t => t.status === 'completed').length;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10 shadow-sm">
        <div className="max-w-6xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-semibold text-gray-900">Lộ trình học tập</h1>
              <p className="text-sm text-gray-500 mt-0.5">{user.full_name || user.email}</p>
            </div>
            <div className="flex items-center gap-2">
              {(user.roles.includes('mentor') || user.roles.includes('admin')) && (
                <button
                  onClick={() => router.push('/mentor')}
                  className="px-3 py-2 bg-gradient-to-r from-[#1E90FF] to-[#9333ea] text-white rounded-lg hover:opacity-90 text-sm font-medium transition-all shadow-sm"
                >
                  Mentor Dashboard
                </button>
              )}
              <button
                onClick={() => router.push('/dashboard')}
                className="px-3 py-2 text-sm text-gray-600 hover:text-[#1E90FF] hover:bg-blue-50 rounded-lg transition-colors"
              >
                ← Quay lại
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-6 space-y-6">
        {/* Progress Stats */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <div className="bg-white rounded-xl p-4 border border-gray-200 shadow-sm">
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Level</p>
            <p className="text-2xl font-semibold text-[#1E90FF] mt-1">{user.level}</p>
          </div>
          <div className="bg-white rounded-xl p-4 border border-gray-200 shadow-sm">
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Tổng XP</p>
            <p className="text-2xl font-semibold text-[#9333ea] mt-1">{user.current_xp}</p>
          </div>
          <div className="bg-white rounded-xl p-4 border border-gray-200 shadow-sm">
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Đang làm</p>
            <p className="text-2xl font-semibold text-[#FFA500] mt-1">{inProgressCount}</p>
          </div>
          <div className="bg-white rounded-xl p-4 border border-gray-200 shadow-sm">
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Hoàn thành</p>
            <p className="text-2xl font-semibold text-[#32CD32] mt-1">{completedCount}</p>
          </div>
        </div>

        {/* Tabs */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
          <div className="border-b border-gray-200">
            <nav className="flex">
              <button
                onClick={() => setActiveTab('available')}
                className={`flex-1 sm:flex-none px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === 'available'
                    ? 'border-[#1E90FF] text-[#1E90FF]'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                Có thể làm ({availableTasks.length})
              </button>
              <button
                onClick={() => setActiveTab('my-tasks')}
                className={`flex-1 sm:flex-none px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === 'my-tasks'
                    ? 'border-[#1E90FF] text-[#1E90FF]'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                Tasks của tôi ({myTasks.length})
              </button>
            </nav>
          </div>

          {/* Content */}
          <div className="p-4 lg:p-6">
            {loading ? (
              <div className="text-center py-12 text-gray-500">Đang tải...</div>
            ) : activeTab === 'available' ? (
              <div className="space-y-4">
                {availableTasks.length === 0 ? (
                  <div className="text-center py-12 text-gray-500">
                    Không có task nào khả dụng
                  </div>
                ) : (
                  availableTasks.map((task) => (
                    <div key={task.id} className="border border-gray-200 rounded-lg p-4 hover:border-[#1E90FF]/50 hover:shadow-sm transition-all">
                      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between mb-2">
                            <div className="flex flex-wrap items-center gap-2">
                              <span className={`px-2 py-0.5 text-xs font-medium rounded ${
                                task.type === 'core' ? 'bg-red-100 text-red-700' : 'bg-[#1E90FF]/10 text-[#1E90FF]'
                              }`}>
                                {task.type === 'core' ? 'CORE' : 'BOUNTY'}
                              </span>
                              <span className={`px-2 py-0.5 text-xs font-medium rounded ${DIFFICULTY_COLORS[task.difficulty]}`}>
                                {task.difficulty.toUpperCase()}
                              </span>
                              <span className="text-xs text-gray-500">Level {task.min_level_required}+</span>
                            </div>
                            {(task as any).creator_name && (
                              <div className="px-2 py-1 bg-violet-100 text-violet-700 rounded text-xs font-medium whitespace-nowrap">
                                👤 {(task as any).creator_name}
                              </div>
                            )}
                          </div>
                          <h3 className="text-base font-medium text-gray-900 mb-1">{task.title}</h3>
                          <p className="text-sm text-gray-600 mb-3 line-clamp-2">{task.description}</p>
                          {task.skill_tags.length > 0 && (
                            <div className="flex flex-wrap gap-1.5 mb-3">
                              {task.skill_tags.slice(0, 4).map((skill, idx) => (
                                <span key={idx} className="px-2 py-0.5 bg-gray-100 text-gray-600 text-xs rounded">
                                  {skill}
                                </span>
                              ))}
                              {task.skill_tags.length > 4 && (
                                <span className="text-xs text-gray-500">+{task.skill_tags.length - 4}</span>
                              )}
                            </div>
                          )}
                          <p className="text-sm font-medium text-[#32CD32]">+{task.xp_reward} XP</p>
                        </div>
                        <button
                          onClick={() => handleStartTask(task.id)}
                          className="w-full sm:w-auto px-4 py-2.5 bg-[#1E90FF] text-white rounded-lg hover:bg-[#1a7de0] text-sm font-medium transition-colors flex-shrink-0 shadow-sm"
                        >
                          Bắt đầu
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            ) : (
              <div className="space-y-4">
                {myTasks.length === 0 ? (
                  <div className="text-center py-12 text-gray-500">
                    Bạn chưa có task nào
                  </div>
                ) : (
                  myTasks.map((userTask) => (
                    <div key={userTask.id} className="border border-gray-200 rounded-lg p-4">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className={`px-2 py-0.5 text-xs font-medium rounded ${
                            userTask.task.type === 'core' ? 'bg-red-100 text-red-700' : 'bg-[#1E90FF]/10 text-[#1E90FF]'
                          }`}>
                            {userTask.task.type === 'core' ? 'CORE' : 'BOUNTY'}
                          </span>
                          <span className={`px-2 py-0.5 text-xs font-medium rounded ${STATUS_COLORS[userTask.status]}`}>
                            {userTask.status.toUpperCase().replace('_', ' ')}
                          </span>
                          {(userTask.task as any).creator_name && (
                            <span className="px-2 py-0.5 bg-violet-100 text-violet-700 text-xs font-medium rounded whitespace-nowrap">
                              👤 {(userTask.task as any).creator_name}
                            </span>
                          )}
                        </div>
                        <span className="text-xs text-emerald-600 font-medium">+{userTask.task.xp_reward} XP</span>
                      </div>
                      <h3 className="text-base font-medium text-gray-900 mb-1">{userTask.task.title}</h3>
                      <p className="text-sm text-gray-600 mb-3">{userTask.task.description}</p>
                      
                      {userTask.status === 'in_progress' && (
                        <Link
                          href={`/candidate/tasks/${userTask.id}`}
                          className="inline-block px-4 py-2 bg-[#32CD32] text-white rounded-lg hover:bg-[#22c55e] text-sm font-medium transition-colors shadow-sm"
                        >
                          Nộp bài
                        </Link>
                      )}
                      
                      {userTask.status === 'submitted' && (
                        <div className="text-sm text-gray-600 space-y-1">
                          <p>Đã nộp: {new Date(userTask.submitted_at!).toLocaleString('vi-VN')}</p>
                          {userTask.proof_link && (
                            <a href={userTask.proof_link} target="_blank" rel="noopener noreferrer" className="text-[#1E90FF] hover:underline block truncate">
                              {userTask.proof_link}
                            </a>
                          )}
                        </div>
                      )}
                      
                      {userTask.status === 'completed' && (
                        <div className="text-sm">
                          <p className="text-[#32CD32] font-medium">✓ Hoàn thành! +{userTask.xp_earned} XP</p>
                          {userTask.mentor_comment && (
                            <p className="text-gray-600 mt-1">Nhận xét: {userTask.mentor_comment}</p>
                          )}
                        </div>
                      )}
                      
                      {userTask.status === 'rejected' && (
                        <div className="text-sm">
                          <p className="text-red-600 font-medium">✗ Chưa đạt</p>
                          {userTask.mentor_comment && (
                            <p className="text-gray-600 mt-1">Nhận xét: {userTask.mentor_comment}</p>
                          )}
                          <Link
                            href={`/candidate/tasks/${userTask.id}`}
                            className="inline-block mt-2 px-4 py-2 bg-[#1E90FF] text-white rounded-lg hover:bg-[#1a7de0] text-sm font-medium transition-colors shadow-sm"
                          >
                            Làm lại
                          </Link>
                        </div>
                      )}
                    </div>
                  ))
                )}
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
