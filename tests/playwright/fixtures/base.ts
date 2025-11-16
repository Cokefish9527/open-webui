import { test as base, expect } from "@playwright/test";
import { ArtifactManager } from "../helpers/artifact-manager";
import { registerPageInstrumentation } from "../helpers/logger";
import { BackendLogTailer } from "../helpers/backend-log-tailer";
import { ScenarioContext, createEmptyContext } from "../helpers/context-state";
import { captureWebsocketHealth, detailedWebsocketTest } from "../helpers/websocket-health";

const DEFAULT_ACCOUNT_POOL = Array.from({ length: 10 }, (_, idx) =>
  `test${String(idx + 1).padStart(3, "0")}@hsai.cc`,
);

type TestFixtures = {
  contextState: ScenarioContext;
  artifacts: ArtifactManager;
  accountPool: string[];
};

export const test = base.extend<TestFixtures>({
  contextState: async ({}, use) => {
    await use(createEmptyContext());
  },
  artifacts: async ({}, use, testInfo) => {
    const manager = new ArtifactManager(testInfo);
    await use(manager);
  },
  accountPool: async ({}, use) => {
    const override = process.env.E2E_ACCOUNTS?.split(",").map((item) => item.trim()).filter(Boolean);
    await use(override && override.length ? override : DEFAULT_ACCOUNT_POOL);
  },
  page: async ({ page, artifacts }, use) => {
    const frontendLog = artifacts.pathFor("frontend-log");
    registerPageInstrumentation(page, { frontendLogPath: frontendLog });
    artifacts.trackFile("frontend-log", frontendLog);

    const backendLogPath = artifacts.pathFor("backend-log");
    const backendTailer = new BackendLogTailer(backendLogPath);
    backendTailer.start();
    artifacts.trackFile("backend-log", backendLogPath);

    await use(page);

    backendTailer.stop();
  },
});

export { expect };
export type { ScenarioContext };

test.afterEach(async ({ page, artifacts, contextState }) => {
  try {
    if (!page.isClosed()) {
      // 捕获WebSocket健康状态
      const wsReport = await captureWebsocketHealth(page);
      artifacts.writeJSON("ws-health", wsReport);
      
      // 如果WebSocket连接失败，进行详细诊断
      if (!wsReport.connection || !(wsReport.connection as Record<string, unknown>).success) {
        const detailedReport = await detailedWebsocketTest(page);
        artifacts.writeJSON("ws-detailed", detailedReport);
      }
    }
  } catch {
    // ignore diagnostic errors
  }
  artifacts.writeJSON("context-state", contextState);
});

// 导出一个辅助函数用于登录
export async function loginWithTestAccount(page: any, accountPool: string[]) {
  // 导航到登录页面
  await page.goto("/login");
  
  // 使用测试账号登录
  const testAccount = accountPool[0];
  const testPassword = process.env.E2E_TEST_ACCOUNT_PASSWORD || "H@SaiAutoTest2025!";
  
  await page.fill('[id="email"]', testAccount);
  await page.fill('[id="password"]', testPassword);
  await page.click('button[type="submit"]');
  
  // 等待登录完成
  await page.waitForTimeout(3000);
  
  // 验证登录成功
  await expect(page).not.toHaveURL(/login/);
}