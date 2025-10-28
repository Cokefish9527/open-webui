const fs = require('fs');
const path = require('path');
const {
	loadCredentials,
	createContext,
	humanDelay,
	slowType,
	captureArtifact,
	persistCookies,
	injectCookies,
	gracefulClose
} = require('./shared');

function ensureAbsolute(filePath) {
	if (!filePath) return null;
	return path.isAbsolute(filePath) ? filePath : path.join(process.cwd(), filePath);
}

async function waitForUploadMount(page, timeout = 60000) {
	const start = Date.now();
	while (Date.now() - start < timeout) {
		const ready = await page.$('[data-e2e="upload-progress"], [data-e2e="cover-selector"]');
		if (ready) return true;
		const error = await detectUploadError(page);
		if (error) throw new Error(error);
		await page.waitForTimeout(1000);
	}
	throw new Error('上传界面未在预期时间内加载，请检查账号或页面结构');
}

async function waitForUploadComplete(page, { timeout = 180000, pollInterval = 1500 } = {}) {
	const start = Date.now();
	let lastProgress = 0;

	while (Date.now() - start < timeout) {
		const completed = await page.$('[data-e2e="upload-complete"], [data-e2e="success-result"]');
		if (completed) return true;

		const progress = await page.evaluate(() => {
			const node = document.querySelector('[data-e2e="upload-progress"] progress, [data-e2e="upload-progress"]');
			if (!node) return null;
			if (node.tagName === 'PROGRESS') {
				return Number(node.value || 0);
			}
			const aria = node.getAttribute('aria-valuenow');
			return aria ? Number(aria) : null;
		});

		if (progress !== null) {
			lastProgress = progress;
		}

		const error = await detectUploadError(page);
		if (error) throw new Error(error);

		await page.waitForTimeout(pollInterval);
	}

	throw new Error(`视频上传超时，最近进度 ${lastProgress}%`);
}

async function detectUploadError(page) {
	const errorSelectors = [
		'[data-e2e="upload-error"]',
		'[data-e2e="error-message"]',
		'[data-e2e="upload-failed"]',
		'text="Upload failed"',
		'text="Unsupported file"'
	];

	for (const selector of errorSelectors) {
		const handle = await page.$(selector);
		if (handle) {
			const text = await handle.innerText().catch(() => null);
			return text || '检测到上传错误提示';
		}
	}
	return null;
}

async function fillCaption(page, caption) {
	if (!caption) return;

	const textAreas = [
		'textarea[data-e2e="caption"]',
		'textarea[data-e2e="caption-textarea"]',
		'textarea'
	];

	for (const selector of textAreas) {
		const element = await page.$(selector);
		if (element) {
			await element.click({ clickCount: 3 });
			await humanDelay(page);
			await slowType(element, caption);
			return true;
		}
	}

	return false;
}

async function publish(page) {
	const publishSelectors = [
		'button[data-e2e="post-button"]',
		'button[data-e2e="publish-button"]',
		'button[type="submit"]'
	];

	for (const selector of publishSelectors) {
		const button = await page.$(selector);
		if (button) {
			await button.click();
			return true;
		}
	}
	return false;
}

async function waitForSuccess(page) {
	const successSelectors = [
		'[data-e2e="upload-complete"]',
		'[data-e2e="success-result"]',
		'[data-e2e="redirect-to-videos"]',
		'[data-e2e="post-success"]'
	];

	for (let i = 0; i < 5; i++) {
		for (const selector of successSelectors) {
			const element = await page.$(selector);
			if (element) return true;
		}
		await page.waitForTimeout(2000);
	}

	return false;
}

async function execute(request) {
	const { account, arguments: args = {}, metadata = {} } = request || {};
	if (!account) {
		throw new Error('请求缺少 account 配置');
	}

	const runId = metadata.run_id || `${Date.now()}`;
	const credentials = await loadCredentials(account.encrypted_credentials_ref);
	const { context, page } = await createContext(account, metadata);
	const artifactMetadata = {
		tenant_id: metadata.tenant_id,
		account_id: account.id || account.account_id,
		run_id: runId
	};

	const mediaAssets = args.media_assets || {};
	const videoPath = ensureAbsolute(mediaAssets.video || mediaAssets.video_path);
	if (!videoPath || !fs.existsSync(videoPath)) {
		throw new Error(`未找到要上传的视频文件: ${videoPath || '未知路径'}`);
	}

	try {
		await injectCookies(context, credentials);

		await page.goto('https://www.tiktok.com/upload?lang=en', {
			waitUntil: 'domcontentloaded'
		});
		await humanDelay(page, 800, 1500);
		await captureArtifact(page, runId, 'landing', artifactMetadata).catch(() => null);

		const fileInput =
			(await page.$('input[type="file"][accept*="video"]')) ||
			(await page.$('input[type="file"]'));

		if (!fileInput) {
			throw new Error('未找到上传文件输入框，可能页面结构发生变化');
		}

		await fileInput.setInputFiles(videoPath);
		await humanDelay(page, 1200, 2000);

		await waitForUploadMount(page);
		await captureArtifact(page, runId, 'upload-progress', artifactMetadata).catch(() => null);
		await waitForUploadComplete(page);

		// 填充标题/文案
		const caption =
			args.caption ||
			args.metadata?.caption ||
			(mediaAssets.caption ?? null) ||
			'';
		await fillCaption(page, caption);

		let captionBox = await page.$('textarea[data-e2e="caption"]');
		if (!captionBox) {
			captionBox = await page.$('textarea');
		}

		if (Array.isArray(args.metadata?.hashtags)) {
			const hashtags = args.metadata.hashtags.filter(Boolean);
			for (const tag of args.metadata.hashtags) {
				if (!captionBox) break;
				await slowType(
					captionBox,
					` #${String(tag).replace(/^#/, '')} `
				);
				await humanDelay(page, 200, 400);
			}
		}

		const published = await publish(page);
		if (!published) {
			throw new Error('未能触发发布按钮，请检查页面结构或账号权限');
		}

		const success = await waitForSuccess(page);
		const screenshotPath = await captureArtifact(
			page,
			runId,
			success ? 'publish-success' : 'publish-pending',
			artifactMetadata
		);
		const cookiesPath = await persistCookies(context, credentials);

		return {
			status: success ? 'ok' : 'error',
			message: success ? '视频发布成功' : '视频发布流程未检测到成功提示，请人工确认',
			artifacts: {
				video_path: path.relative(process.cwd(), videoPath),
				caption,
				hashtags: Array.isArray(args.metadata?.hashtags) ? args.metadata.hashtags : [],
				screenshot_path: path.relative(process.cwd(), screenshotPath),
				cookies_path: cookiesPath ? path.relative(process.cwd(), cookiesPath) : null,
				published_at: success ? Date.now() : null,
				publish_status: success ? 'published' : 'pending_verification',
				tenant_id: metadata.tenant_id || null,
				account_id: account.id || null,
				run_id: runId
			}
		};
	} catch (error) {
		console.error('[tiktok_publish_video] 发布失败', error);
		const failureShot = await captureArtifact(page, runId, 'publish-error', artifactMetadata).catch(() => null);
		return {
			status: 'error',
			message: error.message,
			artifacts: {
				video_path: path.relative(process.cwd(), videoPath),
				screenshot_path: failureShot ? path.relative(process.cwd(), failureShot) : null,
				tenant_id: metadata.tenant_id || null,
				account_id: account.id || null,
				run_id: runId
			}
		};
	} finally {
		await gracefulClose(context);
	}
}

module.exports = { execute };

if (require.main === module) {
	(async () => {
		try {
			const payload = JSON.parse(process.argv[2] || '{}');
			const res = await execute(payload);
			console.log(JSON.stringify(res));
		} catch (error) {
			console.error(error);
			process.exit(1);
		}
	})();
}
