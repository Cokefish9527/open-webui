import { test, expect, loginWithTestAccount } from '../fixtures/base';
import type { Page } from '@playwright/test';

const runFull = process.env.E2E_RUN_FULL === 'true';

async function ensureLanding(page: Page) {
	await page.goto('/');
	await expect(page).toHaveTitle(/华商 AI/i);
}

test.describe('S1-ONBOARD', () => {
	test('首登策略引导', async ({ page, contextState, accountPool }) => {
		await ensureLanding(page);

		if (!runFull) {
			test
				.info()
				.annotations.push({
					type: 'note',
					description: 'Full onboarding flow gated by E2E_RUN_FULL'
				});
			return;
		}

		// 使用测试账号登录
		await loginWithTestAccount(page, accountPool);

		// 检查是否存在策略引导相关元素
		const strategyGuide = await page.$('text=战略引导');
		if (strategyGuide) {
			// 如果存在策略引导，模拟完成引导流程
			await page.click('button:has-text("下一步")');
			await page.waitForTimeout(1000);
			await page.click('button:has-text("完成")');
		}

		// 设置上下文状态
		contextState.auth = {
			email: accountPool[0],
			tenantId: 'test-tenant-id',
			token: 'test-token'
		};
		contextState.strategy = { strategyId: 'test-strategy-id', roadmapVersion: 'v1.0' };
	});
});

test.describe('S2-MATERIAL', () => {
	test('素材管理冒烟', async ({ page, contextState, accountPool }) => {
		// 登录
		await loginWithTestAccount(page, accountPool);

		if (!runFull) {
			test.info().annotations.push({ type: 'note', description: '素材上传脚本将在后续实现' });
			return;
		}

		// 导航到素材管理页面
		await page.click('text=素材管理');
		await page.waitForTimeout(2000);

		// 检查页面元素
		await expect(page.locator('text=素材库')).toBeVisible();

		// 初始化素材列表
		contextState.materials = contextState.materials || [];
	});
});

test.describe('S3-WORKFLOW', () => {
	test('对话工作流串联', async ({ page, contextState, accountPool }) => {
		// 登录
		await loginWithTestAccount(page, accountPool);

		if (!runFull) {
			test
				.info()
				.annotations.push({ type: 'note', description: 'Workflow orchestration steps gated' });
			return;
		}

		// 导航到对话工作台
		await page.click('text=对话工作台');
		await page.waitForTimeout(2000);

		// 检查页面元素
		await expect(page.locator('text=AI对话')).toBeVisible();

		// 设置工作流上下文
		contextState.workflow = {
			cardId: 'test-card-id',
			taskId: 'test-task-id',
			videoId: 'test-video-id'
		};
	});
});

test.describe('S4-PUBLISH', () => {
	test('多平台发布流程', async ({ page, contextState, accountPool }) => {
		// 登录
		await loginWithTestAccount(page, accountPool);

		if (!runFull) {
			test.info().annotations.push({ type: 'note', description: 'Publish automation TODO' });
			return;
		}

		// 导航到发布页面
		await page.click('text=内容发布');
		await page.waitForTimeout(2000);

		// 检查页面元素
		await expect(page.locator('text=发布管理')).toBeVisible();

		// 设置发布上下文
		contextState.publish = {
			jobId: 'test-publish-job-id',
			platforms: ['tiktok', 'douyin']
		};
	});
});

test.describe('S5-ANALYTICS', () => {
	test('数据看板回流', async ({ page, contextState, accountPool }) => {
		// 登录
		await loginWithTestAccount(page, accountPool);

		if (!runFull) {
			test.info().annotations.push({ type: 'note', description: 'Analytics checks gated' });
			return;
		}

		// 导航到数据分析页面
		await page.click('text=数据分析');
		await page.waitForTimeout(2000);

		// 检查页面元素
		await expect(page.locator('text=数据看板')).toBeVisible();

		// 设置分析上下文
		contextState.analytics = {
			snapshotAt: new Date().toISOString(),
			metrics: {
				play_count: 100,
				like_count: 50,
				share_count: 20
			}
		};
	});
});
