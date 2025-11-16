import { ChildProcessWithoutNullStreams, spawn } from "child_process";
import fs from "fs";

export class BackendLogTailer {
  private proc?: ChildProcessWithoutNullStreams;
  private logStream?: fs.WriteStream;

  constructor(private readonly logPath: string) {}

  start(): void {
    // 尝试多种后端日志捕获命令
    const commands = [
      process.env.E2E_BACKEND_LOG_CMD,
      "docker compose logs open-webui-backend -f",
      "tail -f logs/backend.log",
      "journalctl -f -u open-webui",
      // 默认命令，如果都没有设置则创建一个提示文件
    ];

    let command = commands.find(cmd => cmd && cmd.trim() !== "");
    
    if (!command) {
      fs.writeFileSync(
        this.logPath,
        "Set E2E_BACKEND_LOG_CMD to capture backend logs. Current run did not stream backend output.\n",
        "utf8",
      );
      return;
    }

    this.logStream = fs.createWriteStream(this.logPath, { flags: "a" });
    
    // 添加时间戳前缀
    const timestamp = new Date().toISOString();
    this.logStream.write(`\n[${timestamp}] Starting backend log capture with command: ${command}\n`);
    
    this.proc = spawn(command, {
      shell: true,
      env: process.env,
    });

    this.proc.stdout.on("data", (chunk: Buffer) => {
      const timestamp = new Date().toISOString();
      const prefixedChunk = chunk.toString().split('\n').map((line: string) => 
        line.trim() !== '' ? `[${timestamp}] ${line}` : line
      ).join('\n');
      this.logStream?.write(prefixedChunk);
    });
    
    this.proc.stderr.on("data", (chunk: Buffer) => {
      const timestamp = new Date().toISOString();
      const prefixedChunk = chunk.toString().split('\n').map((line: string) => 
        line.trim() !== '' ? `[${timestamp}] [ERROR] ${line}` : line
      ).join('\n');
      this.logStream?.write(prefixedChunk);
    });
    
    this.proc.on("close", () => {
      const timestamp = new Date().toISOString();
      this.logStream?.write(`\n[${timestamp}] [tailer] backend log process exited\n`);
    });
    
    this.proc.on("error", (error: Error) => {
      const timestamp = new Date().toISOString();
      this.logStream?.write(`\n[${timestamp}] [tailer] backend log process error: ${error.message}\n`);
    });
  }

  stop(): void {
    if (this.proc) {
      this.proc.kill();
    }
    if (this.logStream) {
      const timestamp = new Date().toISOString();
      this.logStream.write(`\n[${timestamp}] [tailer] stopping log capture\n`);
      this.logStream.close();
    }
  }
}