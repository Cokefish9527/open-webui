import fs from "fs";
import path from "path";
import { TestInfo } from "@playwright/test";

const ARTIFACT_ROOT = path.resolve(process.cwd(), "tests", "playwright", "artifacts");

function sanitizeSegment(value: string): string {
  return value
    .replace(/[^a-zA-Z0-9-_]+/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "")
    .toLowerCase();
}

export class ArtifactManager {
  readonly scenarioDir: string;

  constructor(private readonly testInfo: TestInfo) {
    const slug = sanitizeSegment(testInfo.titlePath.join("__")) || "scenario";
    this.scenarioDir = path.join(ARTIFACT_ROOT, slug);
    fs.mkdirSync(this.scenarioDir, { recursive: true });
  }

  pathFor(name: string, extension = "log"): string {
    const safeName = sanitizeSegment(name) || "artifact";
    return path.join(this.scenarioDir, `${safeName}.${extension}`);
  }

  writeJSON(name: string, payload: unknown): string {
    const filePath = this.pathFor(name, "json");
    fs.writeFileSync(filePath, JSON.stringify(payload, null, 2), "utf8");
    this.testInfo.attachments.push({
      name,
      path: filePath,
      contentType: "application/json",
    });
    return filePath;
  }

  trackFile(name: string, filePath: string, contentType = "text/plain"): void {
    this.testInfo.attachments.push({
      name,
      path: filePath,
      contentType,
    });
  }
  
  // 添加截图功能
  async takeScreenshot(page: any, name: string): Promise<string> {
    const filePath = this.pathFor(name, "png");
    await page.screenshot({ path: filePath, fullPage: true });
    this.testInfo.attachments.push({
      name,
      path: filePath,
      contentType: "image/png",
    });
    return filePath;
  }
  
  // 添加网络跟踪功能
  async startNetworkTrace(page: any, name: string): Promise<string> {
    const filePath = this.pathFor(name, "zip");
    await page.context().tracing.start({ 
      screenshots: true, 
      snapshots: true,
      sources: true
    });
    return filePath;
  }
  
  async stopNetworkTrace(page: any, filePath: string, name: string): Promise<void> {
    await page.context().tracing.stop({ path: filePath });
    this.testInfo.attachments.push({
      name,
      path: filePath,
      contentType: "application/zip",
    });
  }
  
  // 添加HAR文件捕获功能
  async startHARRecording(page: any, name: string): Promise<string> {
    const filePath = this.pathFor(name, "har");
    await page.route("**/*", async (route: any) => {
      await route.continue();
    });
    return filePath;
  }
  
  // 添加文本写入功能
  writeText(name: string, content: string, extension = "txt"): string {
    const filePath = this.pathFor(name, extension);
    fs.writeFileSync(filePath, content, "utf8");
    this.testInfo.attachments.push({
      name,
      path: filePath,
      contentType: "text/plain",
    });
    return filePath;
  }
  
  // 添加二进制文件写入功能
  writeBinary(name: string, buffer: Buffer, extension = "bin"): string {
    const filePath = this.pathFor(name, extension);
    fs.writeFileSync(filePath, buffer);
    this.testInfo.attachments.push({
      name,
      path: filePath,
      contentType: "application/octet-stream",
    });
    return filePath;
  }
}