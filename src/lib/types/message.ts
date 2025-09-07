// 消息类型定义，支持任务系统集成

import type { Task, TaskStep } from './task';

export interface BaseMessage {
	id: string;
	chatId: string;
	parentId: string | null;
	childrenIds: string[];
	role: 'user' | 'assistant' | 'system';
	content: string;
	timestamp: number;
	model?: string;
	done: boolean;
	error?: boolean | { content: string };
	files?: { type: string; url: string; name: string }[];
	sources?: string[];
}

export interface UserMessage extends BaseMessage {
	role: 'user';
	// 用户消息特定属性
}

export interface AssistantMessage extends BaseMessage {
	role: 'assistant';
	// AI助手消息特定属性
	info?: {
		openai?: boolean;
		prompt_tokens?: number;
		completion_tokens?: number;
		total_tokens?: number;
		usage?: unknown;
	};
	annotation?: { type: string; rating: number };
	code_executions?: CodeExecution[];
	feedbackId?: string;
}

export interface SystemMessage extends BaseMessage {
	role: 'system';
	// 系统消息特定属性
}

// 扩展消息类型以支持任务系统
export interface TaskMessage extends AssistantMessage {
	taskId?: string;
	task?: Task;
	taskStep?: TaskStep;
	messageType: 'task_info' | 'task_progress' | 'task_result' | 'task_error';
	// 用于在右侧展示系统信息卡片
	displaySide: 'left' | 'right';
	cardType?: 'task_progress' | 'task_result' | 'material_check' | 'account_check' | 'preview' | 'confirmation' | 'feedback';
	cardData?: any; // 卡片特定数据
}

// 代码执行结果
export interface CodeExecution {
	uuid: string;
	name: string;
	code: string;
	language?: string;
	result?: {
		error?: string;
		output?: string;
		files?: { name: string; url: string }[];
	};
}

// 消息历史结构
export interface MessageHistory {
	messages: Record<string, UserMessage | AssistantMessage | SystemMessage | TaskMessage>;
	currentId: string | null;
}