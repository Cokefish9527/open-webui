const fs = require('fs');
const fsp = fs.promises;
const path = require('path');
const { chromium } = require('playwright');

const DEFAULT_UA =
	'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36';

const ARTIFACT_ROOT =
	process.env.PLAYWRIGHT_ARTIFACT_DIR ||
	path.join(process.cwd(), 'playwright-mcp-artifacts');

async function ensureDir(dirPath) {
	await fsp.mkdir(dirPath, { recursive: true });
	return dirPath;
}

function sanitizeSegment(input, fallback = 'default') {
	if (!input) return fallback;
	return String(input)
		.trim()
		.replace(/[\\/:*?"<>|]+/g, '_')
		.replace(/\s+/g, '_');
}

async function loadCredentials(ref) {
	if (!ref) {
		throw new Error('未提供 credentials_ref，无法加载账号凭证');
	}

	const root = process.env.PLAYWRIGHT_CREDENTIAL_ROOT;
	if (!root) {
		throw new Error('请配置 PLAYWRIGHT_CREDENTIAL_ROOT 以便读取账号凭证');
	}

	const filePath = path.join(root, `${ref}.json`);
	const raw = await fsp.readFile(filePath, 'utf-8');
	return JSON.parse(raw);
}

async function resolveProxy(vpnProfileId) {
	if (!vpnProfileId) return undefined;

	const root = process.env.SOCIAL_VPN_PROXY_DIR || process.env.PLAYWRIGHT_PROXY_DIR;
	if (!root) return undefined;

	const proxyFile = path.join(root, `${vpnProfileId}.json`);
	try {
		const raw = await fsp.readFile(proxyFile, 'utf-8');
		const proxyConfig = JSON.parse(raw);
		if (!proxyConfig.server) {
			throw new Error(`代理配置缺少 server 字段 (${vpnProfileId})`);
		}
		return proxyConfig;
	} catch (error) {
		throw new Error(`加载代理配置失败 (${vpnProfileId}): ${error.message}`);
	}
}

async function createContext(account, metadata = {}) {
	if (!account?.playwright_profile_path) {
		throw new Error('缺失 account.playwright_profile_path 配置');
	}

	const proxy = await resolveProxy(account.vpn_profile_id).catch((err) => {
		throw new Error(`VPN 代理加载失败：${err.message}`);
	});

	const context = await chromium.launchPersistentContext(account.playwright_profile_path, {
		headless: process.env.PLAYWRIGHT_HEADLESS !== 'false',
		viewport: { width: 1280, height: 720 },
		locale: 'en-US',
		userAgent: process.env.PLAYWRIGHT_DESKTOP_UA || DEFAULT_UA,
		proxy,
		args: [
			'--disable-blink-features=AutomationControlled',
			'--disable-dev-shm-usage',
			'--no-sandbox'
		]
	});

	context.setDefaultTimeout(
		Number(process.env.PLAYWRIGHT_DEFAULT_TIMEOUT || 60000)
	);

	const [existing] = context.pages();
	const page = existing || (await context.newPage());

	await page.addInitScript(() => {
		// 混淆 Playwright 指纹
		Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
	});

	return { context, page, proxy };
}

function randomInt(min, max) {
	return Math.floor(Math.random() * (max - min + 1)) + min;
}

async function humanDelay(page, min = 280, max = 620) {
	const delay = randomInt(min, max);
	await page.waitForTimeout(delay);
}

async function slowType(elementHandle, text) {
	for (const char of text) {
		await elementHandle.type(char, { delay: randomInt(40, 120) });
	}
}

async function captureArtifact(page, runId, label, metadata = {}) {
	const safeLabel = label.replace(/[^\w-]/g, '_');
	const safeRun = (runId || `${Date.now()}`).toString().replace(/[^\w-]/g, '_');

	const segments = [ARTIFACT_ROOT];
	if (metadata.tenant_id) {
		segments.push(`tenant_${sanitizeSegment(metadata.tenant_id)}`);
	}
	if (metadata.account_id) {
		segments.push(`account_${sanitizeSegment(metadata.account_id)}`);
	}
	segments.push(safeRun);

	const dir = await ensureDir(path.join(...segments));
	const filePath = path.join(dir, `${safeLabel}-${Date.now()}.png`);
	await page.screenshot({ path: filePath, fullPage: true });
	return filePath;
}

async function persistCookies(context, credentials) {
	if (!credentials?.cookies_path) return null;

	const cookies = await context.cookies();
	await ensureDir(path.dirname(credentials.cookies_path));
	await fsp.writeFile(
		credentials.cookies_path,
		JSON.stringify(cookies, null, 2),
		'utf-8'
	);
	return credentials.cookies_path;
}

async function injectCookies(context, credentials) {
	if (!credentials?.cookies_path) return false;

	try {
		const raw = await fsp.readFile(credentials.cookies_path, 'utf-8');
		const cookies = JSON.parse(raw);
		if (Array.isArray(cookies) && cookies.length > 0) {
			await context.addCookies(cookies);
			return true;
		}
		return false;
	} catch {
		return false;
	}
}

async function gracefulClose(context) {
	try {
		await context?.close();
	} catch (error) {
		console.error('关闭 Playwright 上下文失败', error);
	}
}

module.exports = {
	loadCredentials,
	createContext,
	randomInt,
	humanDelay,
	slowType,
	captureArtifact,
	persistCookies,
	injectCookies,
	gracefulClose,
	ARTIFACT_ROOT
};
