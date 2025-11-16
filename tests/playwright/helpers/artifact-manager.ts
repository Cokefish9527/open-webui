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
}
