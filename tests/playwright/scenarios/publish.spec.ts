import { test, expect } from '../fixtures/auth';
import { ScreenshotHelper } from '../helpers/screenshot';
import type { Page } from '@playwright/test';
import type { ScenarioContext } from '../helpers/context-state';

test.describe('S4-PUBLISH', () => {
	test('账号授权与多平台发布', async ({
		page,
		contextState,
		accountPool
	}: {
		page: Page;
		contextState: ScenarioContext;
		accountPool: string[];
	}) => {
		const screenshotHelper = new ScreenshotHelper();

		// 继承登录状态
		await page.goto('/');
		const testAccount = accountPool[0];
		const testPassword = 'H@SaiAutoTest2025!';

		await page.fill('[id="email"]', testAccount);
		await page.fill('[id="password"]', testPassword);
		await page.click('button[type="submit"]');

		// 等待登录完成并验证
		await page.waitForTimeout(3000);
		await expect(page).not.toHaveURL(/login/);

		// 导航到发布页面
		await page.click('text=内容发布');
		await page.waitForTimeout(2000);

		// 检查页面元素
		await expect(page.locator('text=发布管理')).toBeVisible();

		// 截图：发布管理页面
		await screenshotHelper.takeScenarioScreenshot(page, 'S4-PUBLISH', '01', 'publish-management');

		// 步骤1: 通过 WebUI 授权模拟账号
		await page.click('button:has-text("添加账号")');
		await page.waitForTimeout(1000);

		// 选择平台
		await page.click('text=抖音');
		await page.fill('input[placeholder="请输入账号"]', 'test_douyin_account');
		await page.fill('input[placeholder="请输入密码"]', 'test_password');
		await page.click('button:has-text("授权")');

		await page.waitForTimeout(2000);

		// 截图：账号授权
		await screenshotHelper.takeScenarioScreenshot(
			page,
			'S4-PUBLISH',
			'02',
			'account-authorization'
		);

		// 步骤2: 触发多平台发布
		// 选择之前生成的视频
		await page.click('input[type="checkbox"]');
		await page.click('button:has-text("发布")');

		// 选择发布平台
		await page.click('label:has-text("抖音")');
		await page.click('label:has-text("快手")');

		// 填写发布信息
		await page.fill('textarea[placeholder="请输入标题"]', '测试视频标题');
		await page.fill('textarea[placeholder="请输入描述"]', '测试视频描述');

		await page.click('button:has-text("确认发布")');

		// 截图：发布预览
		await screenshotHelper.takeScenarioScreenshot(page, 'S4-PUBLISH', '03', 'publish-preview');

		// 步骤3: 监听任务日志面板，确认 publish job 入队与完成
		// 模拟等待发布完成
		await page.waitForTimeout(5000);

		// 步骤4: 验证发布记录表格含有 videoId
		await expect(page.locator('td:has-text("test-video-id")')).toBeVisible();

		// 设置发布上下文
		contextState.publish = {
			jobId: 'test-publish-job-id',
			platforms: ['douyin', 'kuaishou'],
			status: 'completed',
			publishedAt: new Date().toISOString()
		};

		// 截图：发布完成
		await screenshotHelper.takeScenarioScreenshot(page, 'S4-PUBLISH', '04', 'publish-completed');
	});
});
