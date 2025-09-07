// 消息工具函数，用于创建不同类型的消息

import { v4 as uuidv4 } from 'uuid';
import { type TaskMessage, type UserMessage, type AssistantMessage, type SystemMessage } from '$lib/types/message';
import { type Task, type TaskStep } from '$lib/types/task';

// 创建用户消息
export function createUserMessage(chatId: string, content: string, userId: string, files?: any[]): UserMessage {
	return {
		id: uuidv4(),
		chatId,
		parentId: null,
		childrenIds: [],
		role: 'user',
		content,
		timestamp: Math.floor(Date.now() / 1000),
		done: true,
		files
	};
}

// 创建AI助手消息
export function createAssistantMessage(chatId: string, content: string, model: string, parentId?: string): AssistantMessage {
	return {
		id: uuidv4(),
		chatId,
		parentId: parentId || null,
		childrenIds: [],
		role: 'assistant',
		content,
		timestamp: Math.floor(Date.now() / 1000),
		model,
		done: true
	};
}

// 创建系统消息
export function createSystemMessage(chatId: string, content: string, parentId?: string): SystemMessage {
	return {
		id: uuidv4(),
		chatId,
		parentId: parentId || null,
		childrenIds: [],
		role: 'system',
		content,
		timestamp: Math.floor(Date.now() / 1000),
		done: true
	};
}

// 创建任务消息
export function createTaskMessage(
	chatId: string, 
	task: Task, 
	step: TaskStep | null,
	messageType: TaskMessage['messageType'],
	displaySide: 'left' | 'right',
	cardType?: string,
	cardData?: any,
	content?: string
): TaskMessage {
	// 根据任务类型和步骤生成默认内容
	if (!content) {
		content = generateTaskMessageContent(task, step, messageType);
	}
	
	return {
		id: uuidv4(),
		chatId,
		parentId: null,
		childrenIds: [],
		role: 'assistant',
		content,
		timestamp: Math.floor(Date.now() / 1000),
		model: 'task-manager',
		done: true,
		taskId: task.id,
		task,
		taskStep: step || undefined,
		messageType,
		displaySide,
		cardType,
		cardData
	};
}

// 根据任务和步骤生成消息内容
function generateTaskMessageContent(task: Task, step: TaskStep | null, messageType: string): string {
	switch (messageType) {
		case 'task_info':
			return `已创建${task.title}，任务ID: ${task.id.substring(0, 8)}`;
		case 'task_progress':
			if (step) {
				return `正在执行步骤: ${step.name} (${task.progress}%)`;
			}
			return `任务进行中 (${task.progress}%)`;
		case 'task_result':
			return `任务已完成: ${task.title}`;
		case 'task_error':
			return `任务执行出错: ${task.error || '未知错误'}`;
		default:
			return '任务状态更新';
	}
}

// 创建素材检查卡片消息
export function createMaterialCheckMessage(chatId: string, task: Task, step: TaskStep, cardData: any): TaskMessage {
	return createTaskMessage(
		chatId,
		task,
		step,
		'task_progress',
		'right',
		'material_check',
		cardData,
		`已完成素材检查: ${cardData.validMaterials?.length || 0}个有效素材, ${cardData.missingMaterials?.length || 0}个缺失素材, ${cardData.issues?.length || 0}个问题需要处理`
	);
}

// 创建账号检查卡片消息
export function createAccountCheckMessage(chatId: string, task: Task, step: TaskStep, cardData: any): TaskMessage {
	return createTaskMessage(
		chatId,
		task,
		step,
		'task_progress',
		'right',
		'account_check',
		cardData,
		`已完成账号检查: ${cardData.accounts?.filter(a => a.status === 'authorized').length || 0}个账号已授权`
	);
}

// 创建预览卡片消息
export function createPreviewMessage(chatId: string, task: Task, step: TaskStep, cardData: any): TaskMessage {
	return createTaskMessage(
		chatId,
		task,
		step,
		'task_progress',
		'right',
		'preview',
		cardData,
		`已生成预览内容，请确认是否发布`
	);
}

// 创建确认卡片消息
export function createConfirmationMessage(chatId: string, task: Task, step: TaskStep, cardData: any): TaskMessage {
	return createTaskMessage(
		chatId,
		task,
		step,
		'task_progress',
		'right',
		'confirmation',
		cardData,
		`请确认发布内容`
	);
}

// 创建反馈卡片消息
export function createFeedbackMessage(chatId: string, task: Task, step: TaskStep, cardData: any): TaskMessage {
	return createTaskMessage(
		chatId,
		task,
		step,
		'task_result',
		'right',
		'feedback',
		cardData,
		`任务已完成，成功率${cardData.successRate}%`
	);
}