import { request, type APIRequestContext } from '@playwright/test';

type ApiClientOptions = {
	baseURL: string;
	token?: string;
};

export class ApiClient {
	private readonly baseURL: string;
	private readonly token?: string;
	private requestContext: APIRequestContext | null = null;

	constructor(options: ApiClientOptions) {
		this.baseURL = options.baseURL;
		this.token = options.token;
	}

	async init(): Promise<void> {
		this.requestContext = await request.newContext({
			baseURL: this.baseURL,
			extraHTTPHeaders: {
				'Content-Type': 'application/json',
				...(this.token ? { Authorization: `Bearer ${this.token}` } : {})
			}
		});
	}

	async close(): Promise<void> {
		if (this.requestContext) {
			await this.requestContext.dispose();
			this.requestContext = null;
		}
	}

	async get(path: string, params?: Record<string, string>): Promise<any> {
		if (!this.requestContext) {
			throw new Error('ApiClient not initialized. Call init() first.');
		}

		const response = await this.requestContext.get(path, { params });
		return await response.json();
	}

	async post(path: string, data: any): Promise<any> {
		if (!this.requestContext) {
			throw new Error('ApiClient not initialized. Call init() first.');
		}

		const response = await this.requestContext.post(path, { data });
		return await response.json();
	}

	async put(path: string, data: any): Promise<any> {
		if (!this.requestContext) {
			throw new Error('ApiClient not initialized. Call init() first.');
		}

		const response = await this.requestContext.put(path, { data });
		return await response.json();
	}

	async delete(path: string): Promise<any> {
		if (!this.requestContext) {
			throw new Error('ApiClient not initialized. Call init() first.');
		}

		const response = await this.requestContext.delete(path);
		return await response.json();
	}

	// 特定于业务的API方法
	async login(email: string, password: string): Promise<{ token: string; user: any }> {
		const response = await this.post('/auth/login', { email, password });
		return response;
	}

	async getMaterials(folder?: string): Promise<any[]> {
		const params = folder ? { folder } : undefined;
		const response = await this.get('/materials', params);
		return response.data || response;
	}

	async createMaterial(material: any): Promise<any> {
		const response = await this.post('/materials', material);
		return response;
	}

	async getWorkflowTasks(): Promise<any[]> {
		const response = await this.get('/workflow/tasks');
		return response.data || response;
	}

	async getAnalyticsMetrics(): Promise<Record<string, number>> {
		const response = await this.get('/analytics/metrics');
		return response.data || response;
	}
}

// 创建一个fixture工厂函数
export async function createApiClient(options: ApiClientOptions): Promise<ApiClient> {
	const client = new ApiClient(options);
	await client.init();
	return client;
}
