import fs from "fs";
import path from "path";
import type { Reporter, TestCase, TestResult } from "@playwright/test/reporter";

function sanitize(value: string): string {
  return value
    .replace(/[^a-zA-Z0-9-_]+/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "")
    .toLowerCase();
}

function buildYaml(test: TestCase, result: TestResult, attachments: Record<string, string>): string {
  const timestamp = result.startTime.toISOString();
  const lines = [
    `id: BUG-${timestamp.replace(/[:.]/g, "-")}-${sanitize(test.title)}`,
    `discovered_at: ${timestamp}`,
    `scenario: ${test.titlePath().join(" > ")}`,
    `status: ${result.status}`,
    `expected: 参见测试用例`,
    `actual: ${(result.error?.message ?? "参见日志").replace(/\r?\n/g, "\\n")}`,
    `account_pool: ${process.env.E2E_ACCOUNTS || "test001@test010@hsai.cc"}`,
    `test_environment: ${process.env.E2E_BASE_URL || "http://localhost:8080"}`,
    `browser: ${test.parent.project()?.name || "unknown"}`,
    `retry_count: ${result.retry}`,
  ];
  
  // 添加附件信息
  Object.entries(attachments).forEach(([name, relPath]) => {
    lines.push(`${name}: ${relPath.replace(/\\/g, "/")}`);
  });
  
  // 添加测试元数据
  const metadata = test.parent.project()?.metadata;
  if (metadata) {
    Object.entries(metadata).forEach(([key, value]) => {
      lines.push(`metadata_${key}: ${String(value)}`);
    });
  }
  
  return lines.join("\n") + "\n";
}

class DefectReporter implements Reporter {
  private bugsDir = path.resolve(process.cwd(), "tests", "playwright", "artifacts", "bugs");

  onBegin(): void {
    fs.mkdirSync(this.bugsDir, { recursive: true });
  }

  onTestEnd(test: TestCase, result: TestResult): void {
    if (result.status === "passed" || result.status === "skipped") {
      return;
    }

    const attachments: Record<string, string> = {};
    for (const attachment of result.attachments) {
      if (attachment.path) {
        const relPath = path.relative(process.cwd(), attachment.path);
        attachments[attachment.name] = relPath.replace(/\\/g, "/");
      }
    }

    const yaml = buildYaml(test, result, attachments);
    const fileName = `BUG-${Date.now()}-${sanitize(test.title)}.yml`;
    fs.writeFileSync(path.join(this.bugsDir, fileName), yaml, "utf8");
  }
  
  // 添加onEnd钩子来生成测试摘要报告
  onEnd(result: { status: string; startTime: Date; duration: number }): void {
    const summary = {
      status: result.status,
      startTime: result.startTime.toISOString(),
      duration: result.duration,
      generatedAt: new Date().toISOString(),
    };
    
    const summaryFile = path.join(this.bugsDir, "test-run-summary.json");
    fs.writeFileSync(summaryFile, JSON.stringify(summary, null, 2), "utf8");
  }
}

export default DefectReporter;