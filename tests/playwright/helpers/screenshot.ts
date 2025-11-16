import fs from "fs";
import path from "path";

// 截图策略实现
export class ScreenshotHelper {
  private readonly artifactsRoot: string;

  constructor() {
    this.artifactsRoot = path.resolve(process.cwd(), "tests", "playwright", "artifacts");
  }

  // 场景级关键节点截图
  async takeScenarioScreenshot(page: any, scenario: string, step: string, description: string): Promise<string> {
    const screenshotDir = path.join(this.artifactsRoot, "screenshots", scenario);
    if (!fs.existsSync(screenshotDir)) {
      fs.mkdirSync(screenshotDir, { recursive: true });
    }

    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const fileName = `${step}-${description}-${timestamp}.png`;
    const filePath = path.join(screenshotDir, fileName);

    await page.screenshot({ path: filePath, fullPage: true });
    return filePath;
  }

  // 失败截图
  async takeFailureScreenshot(page: any, scenario: string, step: string): Promise<string> {
    const screenshotDir = path.join(this.artifactsRoot, "screenshots", scenario);
    if (!fs.existsSync(screenshotDir)) {
      fs.mkdirSync(screenshotDir, { recursive: true });
    }

    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const fileName = `failure-${step}-${timestamp}.png`;
    const filePath = path.join(screenshotDir, fileName);

    await page.screenshot({ path: filePath, fullPage: true });
    return filePath;
  }
}