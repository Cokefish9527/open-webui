import fs from "fs";
import { Page, Request, Response } from "@playwright/test";

interface LoggerOptions {
  frontendLogPath: string;
}

export function registerPageInstrumentation(page: Page, options: LoggerOptions): void {
  const { frontendLogPath } = options;
  fs.writeFileSync(frontendLogPath, "", "utf8");

  const append = (line: string) => {
    const entry = `[${new Date().toISOString()}] ${line}\n`;
    fs.appendFileSync(frontendLogPath, entry, "utf8");
  };

  page.on("console", (message) => {
    append(`[console:${message.type()}] ${message.text()}`);
  });

  page.on("pageerror", (error) => {
    append(`[pageerror] ${error.message}\n${error.stack ?? ""}`);
  });

  page.on("requestfailed", (request: Request) => {
    append(`[requestfailed] ${request.url()} ${request.failure()?.errorText ?? "unknown"}`);
  });

  page.on("response", async (response: Response) => {
    if (response.status() >= 400) {
      append(`[response:${response.status()}] ${response.url()}`);
    }
  });
}
