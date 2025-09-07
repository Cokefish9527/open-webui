// 消息类型定义，支持任务系统集成

// 注意：这里我们使用项目中已有的HSAI任务系统类型定义
// 而不是我们之前设计的独立任务系统类型

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

// 扩展消息类型以支持HSAI任务系统
// 注意：这里我们使用项目中已有的HSAI任务系统类型定义
export interface HSAITaskMessage extends AssistantMessage {
	taskId?: string;
	task?: HSAITask;  // 使用HSAI任务系统中的任务类型
	taskStep?: HSAITaskStep;  // 如果需要，可以定义任务步骤类型
	messageType: 'task_info' | 'task_progress' | 'task_result' | 'task_error';
	// 用于在右侧展示系统信息卡片
	displaySide: 'left' | 'right';
	cardType?: 'task_progress' | 'task_result' | 'material_check' | 'account_check' | 'preview' | 'confirmation' | 'feedback';
	cardData?: any; // 卡片特定数据
}

// HSAI任务系统类型定义（基于后端模型）
export interface HSAITask {
	id: string;
	title: string;
	description?: string;
	task_type: string;
	status: string;
	user_id: string;
	assignee_id?: string;
	chat_id?: string;
	collaborators?: Array<{ user_id: string; role: string; joined_at: number }>;
	shared_sessions?: string[];
	config?: Record<string, any>;
	inputs?: Record<string, any>;
	outputs?: Record<string, any>;
	workflow_id?: string;
	parent_task_id?: string;
	progress: number; // 0-100
	started_at?: number;
	completed_at?: number;
	error_message?: string;
	retry_count: number;
	priority: number;
	tags?: string[];
	created_at: number;
	updated_at: number;
}

// 如果需要，可以定义任务步骤类型
export interface HSAITaskStep {
	id: string;
	taskId: string;
	name: string;
	description: string;
	status: string;
	order: number;
	startedAt?: number;
	completedAt?: number;
	error?: string;
	result?: any;
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
	messages: Record<string, UserMessage | AssistantMessage | SystemMessage | HSAITaskMessage>;
	currentId: string | null;
}