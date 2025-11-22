import { test, expect } from '../fixtures/base';

test.describe('冒烟测试', () => {
	test('验证页面可以正常访问', async ({ page }) => {
		// 访问首页
		await page.goto('/');

		// 验证页面标题
		await expect(page).toHaveTitle(/华商 AI/i);

		// 验证登录表单存在
		const loginForm = page.locator('form');
		await expect(loginForm).toBeVisible();

		console.log('冒烟测试通过：页面可以正常访问');
	});

	test('验证测试账号池', async ({ accountPool }) => {
		// 验证账号池包含10个测试账号
		expect(accountPool).toHaveLength(10);

		// 验证第一个账号格式正确
		expect(accountPool[0]).toMatch(/^test\d{3}@hsai\.cc$/);

		console.log('冒烟测试通过：测试账号池配置正确');
	});
});
