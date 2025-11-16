import { test, expect } from "../fixtures/base";
import type { Page } from "@playwright/test";

const runFull = process.env.E2E_RUN_FULL === "true";

async function ensureLanding(page: Page) {
  await page.goto("/");
  await expect(page).toHaveTitle(/HSAI/i);
}

test.describe("S1-ONBOARD", () => {
  test("首登策略引导", async ({ page, contextState }) => {
    await ensureLanding(page);
    if (!runFull) {
      test.info().annotations.push({ type: "note", description: "Full onboarding flow gated by E2E_RUN_FULL" });
      return;
    }
    contextState.strategy = { strategyId: "pending", roadmapVersion: "TODO" };
  });
});

test.describe("S2-MATERIAL", () => {
  test("素材管理冒烟", async ({ page, contextState }) => {
    await ensureLanding(page);
    if (!runFull) {
      test.info().annotations.push({ type: "note", description: "素材上传脚本将在后续实现" });
      return;
    }
    contextState.materials = contextState.materials || [];
  });
});

test.describe("S3-WORKFLOW", () => {
  test("对话工作流串联", async ({ page, contextState }) => {
    await ensureLanding(page);
    if (!runFull) {
      test.info().annotations.push({ type: "note", description: "Workflow orchestration steps gated" });
      return;
    }
    contextState.workflow = { taskId: "pending" };
  });
});

test.describe("S4-PUBLISH", () => {
  test("多平台发布流程", async ({ page, contextState }) => {
    await ensureLanding(page);
    if (!runFull) {
      test.info().annotations.push({ type: "note", description: "Publish automation TODO" });
      return;
    }
    contextState.publish = { platforms: ["tiktok", "douyin"] };
  });
});

test.describe("S5-ANALYTICS", () => {
  test("数据看板回流", async ({ page, contextState }) => {
    await ensureLanding(page);
    if (!runFull) {
      test.info().annotations.push({ type: "note", description: "Analytics checks gated" });
      return;
    }
    contextState.analytics = { snapshotAt: new Date().toISOString(), metrics: {} };
  });
});
