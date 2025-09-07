// HSAI任务服务，用于与后端HSAI任务系统API交互

import { WEBUI_BASE_URL } from '$lib/constants';
import { type HSAITask, type HSAITaskMessage } from '$lib/types/message';

class HSAITaskService {
	// 获取用户任务列表
	async getUserTasks(
		status?: string,
		taskType?: string,
		assigneeId?: string,
		chatId?: string,
		pageSize: number = 20,
		pageIndex: number = 1
	): Promise<{ data: HSAITask[]; pagination: any }> {
		try {
			const params = new URLSearchParams();
			if (status) params.append('status', status);
			if (taskType) params.append('task_type', taskType);
			if (assigneeId) params.append('assignee_id', assigneeId);
			if (chatId) params.append('chat_id', chatId);
			params.append('ps', pageSize.toString());
			params.append('pi', pageIndex.toString());

			const response = await fetch(
				`${WEBUI_BASE_URL}/hsai/tasks?${params.toString()}`,
				{
					method: 'GET',
					headers: {
						'Content-Type': 'application/json'
					},
					credentials: 'include'
				}
			);

			if (!response.ok) {
				throw new Error(`HTTP error! status: ${response.status}`);
			}

			return await response.json();
		} catch (error) {
			console.error('Error fetching user tasks:', error);
			throw error;
		}
	}

	// 创建新任务
	async createTask(taskData: {
		title: string;
		description?: string;
		task_type: string;
		chat_id?: string;
		config?: Record<string, any>;
		inputs?: Record<string, any>;
		priority?: number;
		tags?: string[];
	}): Promise<HSAITask> {
		try {
			const response = await fetch(`${WEBUI_BASE_URL}/hsai/tasks`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				credentials: 'include',
				body: JSON.stringify(taskData)
			});

			if (!response.ok) {
				throw new Error(`HTTP error! status: ${response.status}`);
			}

			return await response.json();
		} catch (error) {
			console.error('Error creating task:', error);
			throw error;
		}
	}

	// 获取任务详情
	async getTask(taskId: string): Promise<HSAITask> {
		try {
			const response = await fetch(`${WEBUI_BASE_URL}/hsai/tasks/${taskId}`, {
				method: 'GET',
				headers: {
					'Content-Type': 'application/json'
				},
				credentials: 'include'
			});

			if (!response.ok) {
				throw new Error(`HTTP error! status: ${response.status}`);
			}

			return await response.json();
		} catch (error) {
			console.error('Error fetching task:', error);
			throw error;
		}
	}

	// 更新任务
	async updateTask(
		taskId: string,
		updateData: {
			title?: string;
			description?: string;
			status?: string;
			assignee_id?: string;
			config?: Record<string, any>;
			inputs?: Record<string, any>;
			outputs?: Record<string, any>;
			progress?: number;
			error_message?: string;
			priority?: number;
			tags?: string[];
		}
	): Promise<HSAITask> {
		try {
			const response = await fetch(`${WEBUI_BASE_URL}/hsai/tasks/${taskId}`, {
				method: 'PUT',
				headers: {
					'Content-Type': 'application/json'
				},
				credentials: 'include',
				body: JSON.stringify(updateData)
			});

			if (!response.ok) {
				throw new Error(`HTTP error! status: ${response.status}`);
			}

			return await response.json();
		} catch (error) {
			console.error('Error updating task:', error);
			throw error;
		}
	}

	// 启动任务
	async startTask(taskId: string): Promise<HSAITask> {
		try {
			const response = await fetch(`${WEBUI_BASE_URL}/hsai/tasks/${taskId}/start`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				credentials: 'include'
			});

			if (!response.ok) {
				throw new Error(`HTTP error! status: ${response.status}`);
			}

			return await response.json();
		} catch (error) {
			console.error('Error starting task:', error);
			throw error;
		}
	}

	// 取消任务
	async cancelTask(taskId: string): Promise<HSAITask> {
		try {
			const response = await fetch(`${WEBUI_BASE_URL}/hsai/tasks/${taskId}/cancel`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				credentials: 'include'
			});

			if (!response.ok) {
				throw new Error(`HTTP error! status: ${response.status}`);
			}

			return await response.json();
		} catch (error) {
			console.error('Error canceling task:', error);
			throw error;
		}
	}

	// 更新任务进度
	async updateTaskProgress(taskId: string, progress: number): Promise<boolean> {
		try {
			const response = await fetch(`${WEBUI_BASE_URL}/hsai/tasks/${taskId}/progress`, {
				method: 'PUT',
				headers: {
					'Content-Type': 'application/json'
				},
				credentials: 'include',
				body: JSON.stringify({ progress })
			});

			if (!response.ok) {
				throw new Error(`HTTP error! status: ${response.status}`);
			}

			return await response.json();
		} catch (error) {
			console.error('Error updating task progress:', error);
			throw error;
		}
	}

	// 获取任务统计信息
	async getTaskStats(): Promise<any> {
		try {
			const response = await fetch(`${WEBUI_BASE_URL}/hsai/tasks/statistics`, {
				method: 'GET',
				headers: {
					'Content-Type': 'application/json'
				},
				credentials: 'include'
			});

			if (!response.ok) {
				throw new Error(`HTTP error! status: ${response.status}`);
			}

			return await response.json();
		} catch (error) {
			console.error('Error fetching task stats:', error);
			throw error;
		}
	}
}

// 导出单例实例
export const hsaiTaskService = new HSAITaskService();