import { ChildProcessWithoutNullStreams, spawn } from "child_process";
import fs from "fs";

export class BackendLogTailer {
  private proc?: ChildProcessWithoutNullStreams;
  private logStream?: fs.WriteStream;

  constructor(private readonly logPath: string) {}

  start(): void {
    const command = process.env.E2E_BACKEND_LOG_CMD;
    if (!command) {
      fs.writeFileSync(
        this.logPath,
        "Set E2E_BACKEND_LOG_CMD to capture backend logs. Current run did not stream backend output.\n",
        "utf8",
      );
      return;
    }

    this.logStream = fs.createWriteStream(this.logPath, { flags: "a" });
    this.proc = spawn(command, {
      shell: true,
      env: process.env,
    });

    this.proc.stdout.on("data", (chunk: Buffer) => this.logStream?.write(chunk));
    this.proc.stderr.on("data", (chunk: Buffer) => this.logStream?.write(chunk));
    this.proc.on("close", () => this.logStream?.write("\n[tailer] backend log process exited\n"));
  }

  stop(): void {
    this.proc?.kill();
    this.logStream?.close();
  }
}
