import { WEBUI_API_BASE_URL } from '$lib/constants';

type HttpMethod = 'GET' | 'POST';

const request = async <TResponse>(
	token: string,
	method: HttpMethod,
	path: string,
	body?: unknown
): Promise<TResponse> => {
	let error: any = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}${path}`, {
		method,
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		...(body ? { body: JSON.stringify(body) } : {})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json() as Promise<TResponse>;
		})
		.catch((err) => {
			console.error(err);
			error = err;
			return null;
		});

	if (error) {
		throw error;
	}

	return res as TResponse;
};

export interface SocialAccount {
	id: string;
	tenant_id: string;
	platform: string;
	handle: string;
	display_name?: string | null;
	status: 'inactive' | 'active' | 'suspended';
	health_status?: 'unknown' | 'healthy' | 'degraded' | 'blocked';
	vpn_profile_id: string;
	playwright_profile_path?: string;
	last_rotation_at?: number | null;
	created_at: number;
	updated_at?: number | null;
}

export interface CreateAccountPayload {
	platform: string;
	handle: string;
	display_name?: string | null;
	encrypted_credentials_ref?: string | null;
	playwright_profile_path?: string | null;
	vpn_profile_id?: string | null;
	auto_prepare?: boolean;
}

export interface PrepareAccountPayload {
	interactive?: boolean;
	interactive_timeout?: number;
}

export interface MCPExecutionResponse<TArtifacts = Record<string, unknown>> {
	request_id: string;
	status: string;
	message?: string | null;
	artifacts: TArtifacts;
}

export interface SocialPost {
	id: string;
	account_id: string;
	campaign_id?: string | null;
	title?: string | null;
	caption?: string | null;
	media_assets?: Record<string, string> | null;
	metadata?: Record<string, unknown> | null;
	status: string;
	schedule_time?: number | null;
	created_at: number;
	updated_at?: number | null;
}

export interface CreatePostPayload {
	account_id: string;
	title?: string | null;
	caption?: string | null;
	media_assets?: Record<string, string> | null;
	metadata?: Record<string, unknown> | null;
	schedule_time?: number | null;
	campaign_id?: string | null;
}

export interface PublishResponse {
	run: SocialAutomationRun;
	result: Record<string, unknown>;
}

export interface SocialAutomationRun {
	id: string;
	post_id?: string | null;
	trigger_source: string;
	status: string;
	mcp_request_id?: string | null;
	result_payload?: Record<string, unknown> | null;
	screenshot_path?: string | null;
	har_path?: string | null;
	proxy_exit_ip?: string | null;
	duration_ms?: number | null;
	error_reason?: string | null;
	created_at: number;
	updated_at?: number | null;
}

export const listSocialAccounts = (token: string) =>
	request<SocialAccount[]>(token, 'GET', '/social/accounts');

export const createSocialAccount = (token: string, payload: CreateAccountPayload) =>
	request<SocialAccount>(token, 'POST', '/social/accounts', payload);

export const prepareSocialAccount = (token: string, accountId: string, payload: PrepareAccountPayload) =>
	request<MCPExecutionResponse>(token, 'POST', `/social/accounts/${accountId}/prepare`, payload);

export const triggerTikTokLogin = (token: string, accountId: string) =>
	request<MCPExecutionResponse>(token, 'POST', `/social/accounts/${accountId}/tiktok/login`);

export const fetchTikTokCreatorInfo = (
	token: string,
	accountId: string,
	targetHandle: string
) =>
	request<MCPExecutionResponse>(
		token,
		'POST',
		`/social/accounts/${accountId}/tiktok/creator`,
		{ target_handle: targetHandle }
	);

export const fetchTikTokVideoInfo = (token: string, accountId: string, videoUrl: string) =>
	request<MCPExecutionResponse>(
		token,
		'POST',
		`/social/accounts/${accountId}/tiktok/video`,
		{ video_url: videoUrl }
	);

export const listSocialPosts = (token: string, accountId?: string) => {
	const query = accountId ? `?account_id=${encodeURIComponent(accountId)}` : '';
	return request<SocialPost[]>(token, 'GET', `/social/posts${query}`);
};

export const createSocialPost = (token: string, payload: CreatePostPayload) =>
	request<SocialPost>(token, 'POST', '/social/posts', payload);

export const publishSocialPost = (token: string, postId: string) =>
	request<PublishResponse>(token, 'POST', `/social/posts/${postId}/publish`);

