export interface ScenarioContext {
	auth?: {
		email: string;
		tenantId: string;
		token?: string;
	};
	strategy?: {
		strategyId?: string;
		roadmapVersion?: string;
	};
	materials?: Array<{
		id: string;
		type: string;
		ossPath?: string;
		name?: string;
		size?: number;
		uploadedAt?: string;
	}>;
	workflow?: {
		cardId?: string;
		taskId?: string;
		videoId?: string;
		lastEvent?: string;
		status?: string;
	};
	publish?: {
		jobId?: string;
		platforms?: string[];
		status?: string;
		publishedAt?: string;
	};
	analytics?: {
		snapshotAt?: string;
		metrics?: Record<string, number>;
		insights?: Record<string, any>;
	};
	// 通用的临时存储，用于在场景间传递数据
	temp?: Record<string, any>;
}

export function createEmptyContext(): ScenarioContext {
	return {
		materials: []
	};
}

export function mergeContext(
	target: ScenarioContext,
	patch: Partial<ScenarioContext>
): ScenarioContext {
	Object.assign(target, patch);
	return target;
}

// 添加一个函数来保存上下文到文件，以便调试
export function saveContextToFile(context: ScenarioContext, filePath: string): void {
	try {
		const fs = require('fs');
		fs.writeFileSync(filePath, JSON.stringify(context, null, 2), 'utf8');
	} catch (error) {
		console.warn('Failed to save context to file:', error);
	}
}

// 添加一个函数来从文件加载上下文
export function loadContextFromFile(filePath: string): ScenarioContext | null {
	try {
		const fs = require('fs');
		if (fs.existsSync(filePath)) {
			const content = fs.readFileSync(filePath, 'utf8');
			return JSON.parse(content);
		}
	} catch (error) {
		console.warn('Failed to load context from file:', error);
	}
	return null;
}
