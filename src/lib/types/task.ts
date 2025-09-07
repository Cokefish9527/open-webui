// 任务系统类型定义

export interface Task {
	id: string;
	type: TaskType;
	status: TaskStatus;
	createdAt: number;
	updatedAt: number;
	userId: string;
	title: string;
	description?: string;
	parameters?: Record<string, any>;
	result?: any;
	error?: string;
	progress: number; // 0-100
	dependencies?: string[]; // 依赖的其他任务ID
	metadata?: Record<string, any>;
}

export type TaskType = 
	| 'video_synthesis'
	| 'script_generation'
	| 'material_check'
	| 'account_check'
	| 'preview_publish'
	| 'publish_confirmation'
	| 'result_feedback';

export type TaskStatus = 
	| 'pending'
	| 'in_progress'
	| 'completed'
	| 'failed'
	| 'cancelled';

export interface TaskStep {
	id: string;
	taskId: string;
	name: string;
	description: string;
	status: TaskStatus;
	order: number;
	startedAt?: number;
	completedAt?: number;
	error?: string;
	result?: any;
}

// 任务执行历史记录
export interface TaskExecutionHistory {
	id: string;
	taskId: string;
	stepId: string;
	action: string;
	timestamp: number;
	userId?: string;
	data?: Record<string, any>;
}