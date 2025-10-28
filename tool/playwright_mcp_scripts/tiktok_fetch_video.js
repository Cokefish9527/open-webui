const path = require('path');
const {
	createContext,
	humanDelay,
	captureArtifact,
	gracefulClose
} = require('./shared');

async function extractVideoInfo(page) {
	return await page.evaluate(() => {
		const getText = (selector) => {
			const el = document.querySelector(selector);
			return el ? el.textContent?.trim() : null;
		};

		const getAttribute = (selector, attr) => {
			const el = document.querySelector(selector);
			return el ? el.getAttribute(attr) : null;
		};

		const stats = Array.from(document.querySelectorAll('[data-e2e^="browser-share"] span'))
			.map((el) => el.textContent?.trim())
			.filter(Boolean);

		const hashtags = Array.from(document.querySelectorAll('a[href*="tag"]'))
			.map((el) => el.textContent?.trim())
			.filter(Boolean);

		return {
			title: getText('[data-e2e="video-desc"]') || getText('h1[data-e2e="video-desc"]'),
			author: {
				name: getText('[data-e2e="user-title"]'),
				username: getText('[data-e2e="user-subtitle"]')
			},
			stats: {
				likes: getText('[data-e2e="like-count"]'),
				comments: getText('[data-e2e="comment-count"]'),
				shares: getText('[data-e2e="share-count"]')
			},
			publish_time: getText('span[data-e2e="browser-nickname"] + span time'),
			hashtags,
			music: getText('[data-e2e="music-info"]'),
			cover: getAttribute('img[data-e2e="video-cover"]', 'src'),
			video: getAttribute('video', 'src') || getAttribute('video source', 'src'),
			statistics_raw: stats
		};
	});
}

async function execute(request) {
	const { account, arguments: args = {}, metadata = {} } = request || {};
	if (!account) {
		throw new Error('请求缺少 account 配置');
	}
	if (!args.video_url) {
		throw new Error('请在 arguments 中提供 video_url');
	}

	const runId = metadata.run_id || `${Date.now()}`;
	const videoUrl = String(args.video_url);

	const { context, page } = await createContext(account, metadata);
	const artifactMetadata = {
		tenant_id: metadata.tenant_id,
		account_id: account.id || account.account_id,
		run_id: runId
	};

	try {
		await page.goto(videoUrl, { waitUntil: 'networkidle' });
		await humanDelay(page, 800, 1500);

		await page.waitForSelector('[data-e2e="video-desc"]', { timeout: 60000 });

		const videoInfo = await extractVideoInfo(page);
		const screenshotPath = await captureArtifact(page, runId, 'video-info', artifactMetadata);

		return {
			status: 'ok',
			message: '已获取视频信息',
			artifacts: {
				video_url: videoUrl,
				video_info: videoInfo,
				screenshot_path: path.relative(process.cwd(), screenshotPath),
				tenant_id: metadata.tenant_id || null,
				account_id: account.id || null,
				run_id: runId,
				fetched_at: Date.now()
			}
		};
	} catch (error) {
		console.error('[tiktok_fetch_video] 失败', error);
		const failureShot = await captureArtifact(page, runId, 'video-failed', artifactMetadata).catch(() => null);
		return {
			status: 'error',
			message: error.message,
			artifacts: {
				video_url: videoUrl,
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
