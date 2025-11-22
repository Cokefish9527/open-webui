import { defineConfig, devices } from '@playwright/test';
import path from 'path';

const artifactsRoot = path.resolve(process.cwd(), 'tests', 'playwright', 'artifacts');

export default defineConfig({
	testDir: path.resolve(process.cwd(), 'tests', 'playwright', 'scenarios'),
	fullyParallel: true,
	timeout: 3 * 60 * 1000, // 将超时时间从2分钟延长到3分钟
	expect: {
		timeout: 10_000
	},
	forbidOnly: !!process.env.CI,
	retries: process.env.CI ? 1 : 0,
	workers: process.env.CI ? 2 : undefined,
	reporter: [
		['list'],
		['html', { open: 'never', outputFolder: path.join(artifactsRoot, 'html-report') }],
		['./reporters/defect-reporter.ts']
	],
	outputDir: path.join(artifactsRoot, 'results'),
	use: {
		baseURL: process.env.E2E_BASE_URL || 'http://localhost:8080',
		actionTimeout: 15_000,
		navigationTimeout: 30_000,
		ignoreHTTPSErrors: true,
		locale: process.env.E2E_LOCALE || 'zh-CN',
		timezoneId: process.env.E2E_TIMEZONE || 'Asia/Shanghai',
		screenshot: 'only-on-failure',
		video: process.env.CI ? 'retain-on-failure' : 'on-first-retry',
		trace: 'on-first-retry',
		storageState: process.env.E2E_STORAGE_STATE || undefined
	},
	projects: [
		{
			name: 'chromium',
			use: {
				...devices['Desktop Chrome'],
				channel: process.env.E2E_CHROME_CHANNEL || undefined,
				// 添加浏览器启动参数
				launchOptions: {
					args: [
						'--disable-web-security',
						'--disable-features=IsolateOrigins',
						'--disable-site-isolation-trials'
					]
				}
			}
		},
		{
			name: 'firefox',
			use: {
				...devices['Desktop Firefox'],
				// Firefox特定配置
				launchOptions: {
					firefoxUserPrefs: {
						'network.proxy.type': 0,
						'browser.cache.disk.enable': false
					}
				}
			}
		},
		{
			name: 'webkit',
			use: {
				...devices['Desktop Safari'],
				// WebKit特定配置
				launchOptions: {
					args: ['--disable-web-security']
				}
			}
		},

		// 移动端浏览器配置
		{
			name: 'Mobile Chrome',
			use: {
				...devices['Pixel 5'],
				baseURL: process.env.E2E_BASE_URL || 'http://localhost:8080'
			}
		},
		{
			name: 'Mobile Safari',
			use: {
				...devices['iPhone 12'],
				baseURL: process.env.E2E_BASE_URL || 'http://localhost:8080'
			}
		}
	],
	// 添加全局设置
	globalSetup: './global-setup.ts',
	metadata: {
		tenant: '福州华商时代自动化测试',
		accounts: 'test001@hsai.cc ~ test010@hsai.cc',
		testEnvironment: process.env.E2E_BASE_URL || 'http://localhost:8080',
		testType: 'full-journey'
	}
});
