import { test as base, expect } from '@playwright/test';
import { ScenarioContext, createEmptyContext } from '../helpers/context-state';

// 认证相关的fixture，用于处理登录和token管理
export type AuthOptions = {
	email: string;
	password: string;
};

export async function login(page: any, authOptions: AuthOptions): Promise<void> {
	// 导航到登录页面
	await page.goto('/login');

	// 填入登录信息
	await page.fill('[id="email"]', authOptions.email);
	await page.fill('[id="password"]', authOptions.password);
	await page.click('button[type="submit"]');

	// 等待登录完成
	await page.waitForTimeout(3000);

	// 验证登录成功
	await page.waitForURL(/^(?!.*\/login)/);
}

// 创建认证fixture
type AuthFixtures = {
	auth: typeof login;
	contextState: ScenarioContext;
	accountPool: string[];
};

const DEFAULT_ACCOUNT_POOL = Array.from(
	{ length: 10 },
	(_, idx) => `test${String(idx + 1).padStart(3, '0')}@hsai.cc`
);

export const test = base.extend<AuthFixtures>({
	auth: async ({}, use) => {
		await use(login);
	},
	contextState: async ({}, use) => {
		await use(createEmptyContext());
	},
	accountPool: async ({}, use) => {
		const override = process.env.E2E_ACCOUNTS?.split(',')
			.map((item) => item.trim())
			.filter(Boolean);
		await use(override && override.length ? override : DEFAULT_ACCOUNT_POOL);
	}
});

export { expect };
