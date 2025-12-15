import fs from 'fs';
import type { Page, Request, Response } from '@playwright/test';

interface LoggerOptions {
	frontendLogPath: string;
}

export function registerPageInstrumentation(page: Page, options: LoggerOptions): void {
	const { frontendLogPath } = options;
	fs.writeFileSync(frontendLogPath, '', 'utf8');

	const append = (line: string) => {
		const entry = `[${new Date().toISOString()}] ${line}\n`;
		fs.appendFileSync(frontendLogPath, entry, 'utf8');
	};

	page.on('console', (message) => {
		append(`[console:${message.type()}] ${message.text()}`);
	});

	page.on('pageerror', (error) => { 
		append(`[pageerror] ${error.message}\n${error.stack ?? ''}`);
	});

	page.on('requestfailed', (request: Request) => {
		append(`[requestfailed] ${request.url()} ${request.failure()?.errorText ?? 'unknown'}`);
	});

	page.on('response', async (response: Response) => {
		if (response.status() >= 400) {
			append(`[response:${response.status()}] ${response.url()}`);
		}
	});

	// ��������������־
	page.on('request', (request: Request) => {
		// ֻ��¼API���󣬱����¼��̬��Դ
		if (request.url().includes('/api/') || request.url().includes('/ws/')) {
			append(`[request] ${request.method()} ${request.url()}`);
		}
	});

	// ����WebSocket�¼���־
	page.on('websocket', (ws) => {
		append(`[websocket] Connected to ${ws.url()}`);

		ws.on('framesent', (event) => {
			append(`[websocket:out] ${event.payload}`);
		});

		ws.on('framereceived', (event) => {
			append(`[websocket:in] ${event.payload}`);
		});

		ws.on('close', () => {
			append(`[websocket] Closed`);
		});
	});

	// ����ҳ�浼����־
	page.on('framenavigated', (frame) => {
		if (frame === page.mainFrame()) {
			append(`[navigation] ${frame.url()}`);
		}
	});
}
