// 任务服务，用于管理任务的创建、执行和跟踪

import { type Task, type TaskStep, type TaskExecutionHistory, TaskType, TaskStatus } from '$lib/types/task';
import { v4 as uuidv4 } from 'uuid';

class TaskService {
	private tasks: Map<string, Task> = new Map();
	private taskSteps: Map<string, TaskStep> = new Map();
	private executionHistory: TaskExecutionHistory[] = [];

	// 创建新任务
	createTask(type: TaskType, title: string, userId: string, parameters?: Record<string, any>): Task {
		const taskId = uuidv4();
		const task: Task = {
			id: taskId,
			type,
			status: 'pending',
			createdAt: Date.now(),
			updatedAt: Date.now(),
			userId,
			title,
			parameters,
			progress: 0
		};
		
		this.tasks.set(taskId, task);
		this.addToHistory(taskId, 'task_created', { type, title });
		return task;
	}

	// 获取任务
	getTask(taskId: string): Task | undefined {
		return this.tasks.get(taskId);
	}

	// 更新任务状态
	updateTaskStatus(taskId: string, status: TaskStatus, result?: any, error?: string): Task | null {
		const task = this.tasks.get(taskId);
		if (!task) return null;
		
		task.status = status;
		task.updatedAt = Date.now();
		if (result) task.result = result;
		if (error) task.error = error;
		
		this.tasks.set(taskId, task);
		this.addToHistory(taskId, 'status_updated', { status, result, error });
		return task;
	}

	// 更新任务进度
	updateTaskProgress(taskId: string, progress: number): Task | null {
		const task = this.tasks.get(taskId);
		if (!task) return null;
		
		task.progress = Math.min(100, Math.max(0, progress));
		task.updatedAt = Date.now();
		
		this.tasks.set(taskId, task);
		this.addToHistory(taskId, 'progress_updated', { progress });
		return task;
	}

	// 添加任务步骤
	addTaskStep(taskId: string, name: string, description: string, order: number): TaskStep | null {
		const task = this.tasks.get(taskId);
		if (!task) return null;
		
		const stepId = uuidv4();
		const step: TaskStep = {
			id: stepId,
			taskId,
			name,
			description,
			status: 'pending',
			order
		};
		
		this.taskSteps.set(stepId, step);
		this.addToHistory(taskId, 'step_added', { stepId, name, order });
		return step;
	}

	// 更新步骤状态
	updateStepStatus(stepId: string, status: TaskStatus, result?: any, error?: string): TaskStep | null {
		const step = this.taskSteps.get(stepId);
		if (!step) return null;
		
		step.status = status;
		step.updatedAt = Date.now();
		if (result) step.result = result;
		if (error) step.error = error;
		
		this.taskSteps.set(stepId, step);
		this.addToHistory(step.taskId, 'step_status_updated', { stepId, status, result, error });
		
		// 如果步骤完成，检查是否所有步骤都完成以更新任务状态
		if (status === 'completed') {
			this.checkTaskCompletion(step.taskId);
		}
		
		return step;
	}

	// 获取任务的所有步骤
	getTaskSteps(taskId: string): TaskStep[] {
		return Array.from(this.taskSteps.values()).filter(step => step.taskId === taskId);
	}

	// 获取执行历史
	getExecutionHistory(taskId: string): TaskExecutionHistory[] {
		return this.executionHistory.filter(record => record.taskId === taskId);
	}

	// 添加到执行历史
	private addToHistory(taskId: string, action: string, data?: Record<string, any>): void {
		const record: TaskExecutionHistory = {
			id: uuidv4(),
			taskId,
			stepId: data?.stepId || '',
			action,
			timestamp: Date.now(),
			data
		};
		
		this.executionHistory.push(record);
	}

	// 检查任务是否完成
	private checkTaskCompletion(taskId: string): void {
		const task = this.tasks.get(taskId);
		if (!task) return;
		
		const steps = this.getTaskSteps(taskId);
		const allCompleted = steps.length > 0 && steps.every(step => step.status === 'completed');
		
		if (allCompleted) {
			this.updateTaskStatus(taskId, 'completed');
		}
	}

	// 获取用户的任务列表
	getUserTasks(userId: string): Task[] {
		return Array.from(this.tasks.values()).filter(task => task.userId === userId);
	}

	// 删除任务
	deleteTask(taskId: string): boolean {
		const task = this.tasks.get(taskId);
		if (!task) return false;
		
		// 删除相关步骤
		const steps = this.getTaskSteps(taskId);
		steps.forEach(step => {
			this.taskSteps.delete(step.id);
		});
		
		// 删除执行历史
		this.executionHistory = this.executionHistory.filter(record => record.taskId !== taskId);
		
		// 删除任务
		this.tasks.delete(taskId);
		this.addToHistory(taskId, 'task_deleted');
		return true;
	}
}

// 导出单例实例
export const taskService = new TaskService();