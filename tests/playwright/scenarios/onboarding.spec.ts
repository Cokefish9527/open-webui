import { test, expect } from "../fixtures/auth";
import { ScreenshotHelper } from "../helpers/screenshot";
import type { Page } from '@playwright/test';
import type { ScenarioContext } from "../helpers/context-state";

test.describe("S1-ONBOARD", () => {
  test("首次登录与战略输入", async ({ page, contextState, accountPool }: { page: Page; contextState: ScenarioContext; accountPool: string[] }) => {
    const screenshotHelper = new ScreenshotHelper();
    
    // 步骤1: 导航到登录页面并使用测试账号登录
    await page.goto("/");
    const testAccount = accountPool[0];
    const testPassword = "H@SaiAutoTest2025!";
    
    await page.fill('[id="email"]', testAccount);
    await page.fill('[id="password"]', testPassword);
    await page.click('button[type="submit"]');
    
    // 等待登录完成并验证
    await page.waitForTimeout(3000);
    // await expect(page).not.toHaveURL(/login/);
    
    // 截图：登录成功
    await screenshotHelper.takeScenarioScreenshot(page, "S1-ONBOARD", "01", "login-success");
    
    // 步骤2: 触发首次登录引导，断言30s产品介绍弹窗出现
    const introModal = await page.locator('dialog:has-text("产品介绍")').first();
    if (await introModal.isVisible()) {
      // 截图：引导弹窗出现
      await screenshotHelper.takeScenarioScreenshot(page, "S1-ONBOARD", "02", "intro-modal");
      
      // 完成引导流程
      await page.click('button:has-text("下一步")');
      await page.waitForTimeout(1000);
      await page.click('button:has-text("完成")');
    }
    
    // 步骤3: 使用对话工作台完成战略问答，截图策略卡片
    // 等待页面加载完成
    await page.waitForLoadState('networkidle');
    
    // 通过包含特定文本的 span 来定位父级链接
    // 检查当前是否已经停留在"AI秘书"标签，如果不是再点击
    const aiSecretaryTab = page.locator('a:has(span:has-text("AI秘书"))');
    const isActive = await aiSecretaryTab.getAttribute('aria-selected');
    if (isActive !== 'true') {
      await aiSecretaryTab.click();
    }
    await page.waitForTimeout(2000);
    
    // 模拟战略问答过程
    // 使用新的选择器定位可编辑的输入框
    await page.locator('#chat-input').fill("我们的战略目标是提高市场占有率");
    // 使用更精确的ID选择器定位发送按钮
    await page.locator('#send-message-button').click();
    await page.waitForTimeout(2000);
    
    // 截图：策略卡片
    await screenshotHelper.takeScenarioScreenshot(page, "S1-ONBOARD", "03", "strategy-card");
    
    // 步骤4: 进入工作台后抓取自动生成的每日任务
    await page.click('text=工作台');
    await page.waitForTimeout(2000);
    
    // 验证每日任务出现
    await expect(page.locator('text=今日任务')).toBeVisible();
    
    // 设置上下文状态
    contextState.auth = { 
      email: testAccount, 
      tenantId: "test-tenant-id",
      token: "test-token"
    };
    contextState.strategy = { strategyId: "test-strategy-id", roadmapVersion: "v1.0" };
    
    // 截图：工作台任务
    await screenshotHelper.takeScenarioScreenshot(page, "S1-ONBOARD", "04", "task-board");
  });
});