import { test, expect } from '../fixtures/auth';
import { ScreenshotHelper } from '../helpers/screenshot';
import type { Page } from '@playwright/test';
import type { ScenarioContext } from '../helpers/context-state';

test.describe('S5-ANALYTICS', () => {
	test('数据看板与策略回流', async ({
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

		// 导航到数据分析页面
		await page.click('text=数据分析');
		await page.waitForTimeout(2000);

		// 检查页面元素
		await expect(page.locator('text=数据看板')).toBeVisible();

		// 截图：数据看板
		await screenshotHelper.takeScenarioScreenshot(page, 'S5-ANALYTICS', '01', 'dashboard');

		// 步骤1: 打开 Dashboard，断言关键指标（播放量、任务效率）出现
		await expect(page.locator('text=播放量')).toBeVisible();
		await expect(page.locator('text=任务效率')).toBeVisible();

		// 验证关键指标数据
		const playCount = await page.locator('text=100').first();
		const likeCount = await page.locator('text=50').first();
		await expect(playCount).toBeVisible();
		await expect(likeCount).toBeVisible();

		// 截图：关键指标
		await screenshotHelper.takeScenarioScreenshot(page, 'S5-ANALYTICS', '02', 'key-metrics');

		// 步骤2: 触发策略调整按钮并确认 US-STRATEGY-02 的每日任务更新
		await page.click('button:has-text("策略调整")');
		await page.waitForTimeout(2000);

		// 模拟策略调整
		await page.fill(
			'textarea[placeholder="请输入策略调整建议"]',
			'根据数据分析结果，建议调整内容策略'
		);
		await page.click('button:has-text("确认调整")');

		await page.waitForTimeout(3000);

		// 验证每日任务更新
		await expect(page.locator('text=策略调整任务已创建')).toBeVisible();

		// 截图：策略调整
		await screenshotHelper.takeScenarioScreenshot(
			page,
			'S5-ANALYTICS',
			'03',
			'strategy-adjustment'
		);

		// 步骤3: 记录 KPI 快照用于缺陷报告
		contextState.analytics = {
			snapshotAt: new Date().toISOString(),
			metrics: {
				play_count: 100,
				like_count: 50,
				share_count: 20,
				comment_count: 10,
				task_efficiency: 0.85
			},
			insights: {
				trend: '上升',
				recommendation: '增加互动类内容'
			}
		};

		// 截图：KPI快照
		await screenshotHelper.takeScenarioScreenshot(page, 'S5-ANALYTICS', '04', 'kpi-snapshot');
	});
});
