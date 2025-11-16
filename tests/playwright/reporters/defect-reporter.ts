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
    `expected: ${test.description || "参见测试用例"}`,
    `actual: ${(result.error?.message ?? "参见日志").replace(/\r?\n/g, "\\n")}`,
    `account_pool: ${process.env.E2E_ACCOUNTS || "test001@test010@hsai.cc"}`,
  ];
  Object.entries(attachments).forEach(([name, relPath]) => {
    lines.push(`${name}: ${relPath}`);
  });
  if (result.retry) {
    lines.push(`retry: ${result.retry}`);
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
}

export default DefectReporter;
