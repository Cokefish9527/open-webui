const path = require('path');
const {
	createContext,
	humanDelay,
	captureArtifact,
	gracefulClose
} = require('./shared');

async function extractCreatorProfile(page) {
	return await page.evaluate(() => {
		const getText = (selector) => {
			const el = document.querySelector(selector);
			return el ? el.textContent?.trim() : null;
		};

		const followers = getText('[data-e2e="followers-count"]') || getText('strong[data-e2e="followers-count"]');
		const following = getText('[data-e2e="following-count"]') || getText('strong[data-e2e="following-count"]');
		const likes = getText('[data-e2e="likes-count"]') || getText('strong[data-e2e="likes-count"]');
		const bio = getText('[data-e2e="user-bio"]') || getText('div[data-e2e="user-bio"]');

		const avatarEl =
			document.querySelector('[data-e2e="user-avatar"] img') ||
			document.querySelector('img[data-e2e="user-avatar"]');

		return {
			name: getText('[data-e2e="user-title"]') || getText('h1[data-e2e="user-title"]'),
			username: getText('[data-e2e="user-subtitle"]') || getText('h2[data-e2e="user-subtitle"]'),
			followers,
			following,
			likes,
			bio,
			avatar: avatarEl?.src || null
		};
	});
}

async function execute(request) {
	const { account, arguments: args = {}, metadata = {} } = request || {};
	if (!account) {
		throw new Error('请求缺少 account 配置');
	}
	if (!args.target_handle) {
		throw new Error('请在 arguments 中提供 target_handle');
	}

	const runId = metadata.run_id || `${Date.now()}`;
	const targetHandle = String(args.target_handle).replace(/^@/, '');
	const profileUrl = `https://www.tiktok.com/@${targetHandle}`;

	const { context, page } = await createContext(account, metadata);
	const artifactMetadata = {
		tenant_id: metadata.tenant_id,
		account_id: account.id || account.account_id,
		run_id: runId
	};

	try {
		await page.goto(profileUrl, { waitUntil: 'networkidle' });
		await humanDelay(page, 800, 1500);

		// 等待页面核心元素加载
		await page.waitForSelector('[data-e2e="user-title"]', { timeout: 60000 });

		const creator = await extractCreatorProfile(page);
		const screenshotPath = await captureArtifact(page, runId, `creator-${targetHandle}`, artifactMetadata);

		return {
			status: 'ok',
			message: `已获取创作者 ${targetHandle} 信息`,
			artifacts: {
				profile_url: profileUrl,
				creator,
				screenshot_path: path.relative(process.cwd(), screenshotPath),
				tenant_id: metadata.tenant_id || null,
				account_id: account.id || null,
				run_id: runId,
				fetched_at: Date.now()
			}
		};
	} catch (error) {
		console.error('[tiktok_fetch_creator] 失败', error);
		const failureShot = await captureArtifact(page, runId, 'creator-failed', artifactMetadata).catch(() => null);
		return {
			status: 'error',
			message: error.message,
			artifacts: {
				profile_url: profileUrl,
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
