import { Page } from '@playwright/test';

export async function captureWebsocketHealth(page: Page) {
	return page.evaluate(async () => {
		const result: Record<string, unknown> = {};

		try {
			const socketIoType = typeof (window as unknown as { io?: unknown }).io;
			const wsType = typeof WebSocket;
			result.socketIOLoaded = socketIoType !== 'undefined';
			result.webSocketAvailable = wsType !== 'undefined';

			if (socketIoType === 'function') {
				// 获取正确的WebSocket服务器URL
				const baseUrl = window.location.origin;
				const wsUrl = baseUrl.replace(':5173', ':8080').replace(':5174', ':8080');

				// 使用正确的Socket.IO调用方式
				const io = (window as unknown as { io: any }).io;
				const socket = io(wsUrl, {
					path: '/ws/socket.io',
					transports: ['websocket', 'polling'],
					timeout: 10_000
				});

				result.connection = await new Promise((resolve) => {
					const outcome: Record<string, unknown> = {};
					socket.on('connect', () => {
						outcome.success = true;
						outcome.socketId = socket.id;

						// 发送测试消息
						socket.emit('message', { type: 'playwright-probe', timestamp: Date.now() });

						// 监听响应
						socket.on('response', (data: any) => {
							outcome.response = data;
						});

						// 2秒后断开连接
						setTimeout(() => {
							socket.disconnect();
							resolve(outcome);
						}, 2000);
					});

					socket.on('connect_error', (error: Error) => {
						outcome.success = false;
						outcome.error = error.message;
						resolve(outcome);
					});

					socket.on('error', (error: Error) => {
						outcome.success = false;
						outcome.error = error.message;
					});

					setTimeout(() => {
						outcome.success = false;
						outcome.error = 'timeout';
						resolve(outcome);
					}, 10_000);
				});
			}
		} catch (error) {
			result.error = (error as Error).message;
		}

		return result;
	});
}

// 添加一个更详细的WebSocket连接测试函数
export async function detailedWebsocketTest(page: Page) {
	return page.evaluate(async () => {
		const result: Record<string, unknown> = {};

		try {
			// 检查Socket.IO是否存在
			const hasSocketIO = typeof (window as unknown as { io?: unknown }).io === 'function';
			result.hasSocketIO = hasSocketIO;

			if (hasSocketIO) {
				// 获取WebSocket URL
				const baseUrl = window.location.origin;
				const wsUrl = baseUrl.replace(':5173', ':8080').replace(':5174', ':8080');
				result.wsUrl = wsUrl;

				// 使用正确的Socket.IO调用方式
				const io = (window as unknown as { io: any }).io;
				const socket = io(wsUrl, {
					path: '/ws/socket.io',
					transports: ['websocket', 'polling'],
					timeout: 5000,
					reconnection: false
				});

				result.socketState = 'created';

				// 监听连接事件
				socket.on('connect', () => {
					result.connectEvent = true;
					result.socketId = socket.id;
				});

				socket.on('connect_error', (error: Error) => {
					result.connectError = error.message;
				});

				socket.on('error', (error: Error) => {
					result.errorEvent = error.message;
				});

				// 等待一段时间观察连接状态
				await new Promise((resolve) => setTimeout(resolve, 3000));

				result.finalState = socket.connected ? 'connected' : 'disconnected';
				result.finalSocketId = socket.id;

				// 断开连接
				socket.disconnect();
			}
		} catch (error) {
			result.error = (error as Error).message;
		}

		return result;
	});
}
