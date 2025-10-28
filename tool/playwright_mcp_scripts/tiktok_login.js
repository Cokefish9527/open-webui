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

async function ensureLogin(page) {
	// TikTok 在不同地区选择器可能不同，构建一组候选
	const profileSelectors = [
		'[data-e2e="nav-profile"]',
		'[data-e2e="top-login-avatar"]',
		'a[href*="/@"][data-e2e="nav-user-profile"]'
	];

	for (const selector of profileSelectors) {
		const element = await page.$(selector);
		if (element) {
			return true;
		}
	}

	return false;
}

async function performLogin(page, credentials) {
	await page.goto('https://www.tiktok.com/login/phone-or-email/email', {
		waitUntil: 'networkidle'
	});
	await humanDelay(page);

	const usernameInput = await page.waitForSelector('input[name="username"]', {
		timeout: 60000
	});
	await usernameInput.click({ clickCount: 3 });
	await slowType(usernameInput, credentials.username);
	await humanDelay(page);

	const passwordInput = await page.waitForSelector('input[type="password"]', {
		timeout: 60000
	});
	await passwordInput.fill('');
	await slowType(passwordInput, credentials.password || '');
	await humanDelay(page);

	const submitBtn =
		(await page.$('button[data-e2e="login-button"]')) ||
		(await page.$('button[type="submit"]'));

	if (!submitBtn) {
		throw new Error('未找到登录提交按钮，可能页面结构已变更');
	}

	await submitBtn.click();
	await page.waitForLoadState('networkidle', { timeout: 120000 });
	await humanDelay(page, 600, 1200);

	return ensureLogin(page);
}

async function waitForManualLogin(page, timeoutMs = 300000) {
	const start = Date.now();
	while (Date.now() - start < timeoutMs) {
		const loggedIn = await ensureLogin(page);
		if (loggedIn) {
			return true;
		}
		await page.waitForTimeout(2000);
	}
	return false;
}

async function annotateHealth(result, success) {
	return {
		...result,
		artifacts: {
			...result.artifacts,
			health_status: success ? 'healthy' : 'degraded'
		}
	};
}

async function execute(request) {
	const { account, arguments: args = {}, metadata = {} } = request || {};
	if (!account) {
		throw new Error('请求缺少 account 配置');
	}

	const runId = metadata.run_id || `${Date.now()}`;
	const credentials = await loadCredentials(account.encrypted_credentials_ref);
	const interactive = args.interactive === true;
	const interactiveTimeout = Number(
		args.interactive_timeout ||
			process.env.PLAYWRIGHT_INTERACTIVE_TIMEOUT ||
			300000
	);

	const { context, page } = await createContext(account, metadata);

	try {
		// 使用历史 cookie 提升成功率
		await injectCookies(context, credentials);

		await page.goto('https://www.tiktok.com/', { waitUntil: 'networkidle' });
		await humanDelay(page, 800, 1500);

		let loggedIn = await ensureLogin(page);
		if (!loggedIn) {
			const hasCredentials =
				credentials.username && credentials.username.trim().length > 0 &&
				credentials.password && credentials.password.trim().length > 0;

			if (hasCredentials) {
				loggedIn = await performLogin(page, credentials);
			} else if (interactive) {
				console.log(
					'[tiktok_login] 启动交互式登录，请在已打开的浏览器窗口中完成 TikTok 登录。'
				);
				await page.goto('https://www.tiktok.com/login/phone-or-email/email', {
					waitUntil: 'domcontentloaded'
				});
				await humanDelay(page, 800, 1500);
				const success = await waitForManualLogin(page, interactiveTimeout);
				loggedIn = success;
				if (!loggedIn) {
					throw new Error(
						`未在 ${Math.round(interactiveTimeout / 1000)} 秒内检测到登录成功，请重试或补充账号密码`
					);
				}
			} else {
				throw new Error(
					'账号未登录，且凭证中缺少 username/password，无法执行自动登录'
				);
			}
		}

		if (!loggedIn) {
			throw new Error('TikTok 登录失败，请检查账号状态与登录流程');
		}

		const screenshotPath = await captureArtifact(page, runId, 'login-success', {
			tenant_id: metadata.tenant_id,
			account_id: account.id || account.account_id,
			run_id: runId
		});
		const cookiesPath = await persistCookies(context, credentials);

		const result = {
			status: 'ok',
			message: 'TikTok 登录完成',
			artifacts: {
				screenshot_path: path.relative(process.cwd(), screenshotPath),
				cookies_path: cookiesPath ? path.relative(process.cwd(), cookiesPath) : null,
				proxy_exit_ip: metadata.proxy_exit_ip || null,
				login_at: Date.now(),
				tenant_id: metadata.tenant_id || null,
				account_id: account.id || null,
				run_id: runId
			}
		};

		return annotateHealth(result, true);
	} catch (error) {
		console.error('[tiktok_login] 自动化异常', error);
		const failureShot = await captureArtifact(page, runId, 'login-failed', {
			tenant_id: metadata.tenant_id,
			account_id: account.id || account.account_id,
			run_id: runId
		}).catch(() => null);
		const result = {
			status: 'error',
			message: error.message,
			artifacts: {
				screenshot_path: failureShot ? path.relative(process.cwd(), failureShot) : null,
				proxy_exit_ip: metadata.proxy_exit_ip || null,
				tenant_id: metadata.tenant_id || null,
				account_id: account.id || null,
				run_id: runId
			}
		};
		return annotateHealth(result, false);
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
