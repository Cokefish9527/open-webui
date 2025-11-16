import { defineConfig, devices } from "@playwright/test";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const artifactsRoot = path.resolve(__dirname, "artifacts");

export default defineConfig({
  testDir: path.resolve(__dirname, "scenarios"),
  fullyParallel: true,
  timeout: 2 * 60 * 1000,
  expect: {
    timeout: 10_000,
  },
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: process.env.CI ? 2 : undefined,
  reporter: [
    ["list"],
    ["html", { open: "never", outputFolder: path.join(artifactsRoot, "html-report") }],
    [path.join(__dirname, "reporters", "defect-reporter.ts")],
  ],
  outputDir: path.join(artifactsRoot, "results"),
  use: {
    baseURL: process.env.E2E_BASE_URL || "http://localhost:8080",
    actionTimeout: 15_000,
    navigationTimeout: 30_000,
    ignoreHTTPSErrors: true,
    locale: process.env.E2E_LOCALE || "zh-CN",
    timezoneId: process.env.E2E_TIMEZONE || "Asia/Shanghai",
    screenshot: "only-on-failure",
    video: process.env.CI ? "retain-on-failure" : "on-first-retry",
    trace: "on-first-retry",
    storageState: process.env.E2E_STORAGE_STATE || undefined,
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"], channel: process.env.E2E_CHROME_CHANNEL || undefined },
    },
    {
      name: "firefox",
      use: { ...devices["Desktop Firefox"] },
    },
    {
      name: "webkit",
      use: { ...devices["Desktop Safari"] },
    },
  ],
  metadata: {
    tenant: "福州华商时代自动化测试",
    accounts: "test001@hsai.cc ~ test010@hsai.cc",
  },
});


