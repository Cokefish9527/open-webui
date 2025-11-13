import { chromium } from 'playwright';
import fs from 'fs';

async function analyzeSite(url, siteName) {
    console.log(`\n=== 分析 ${siteName} (${url}) ===`);
    
    const browser = await chromium.launch({ headless: false });
    const context = await browser.newContext();
    const page = await context.newPage();
    
    try {
        // 启用控制台日志捕获
        page.on('console', msg => {
            console.log(`[${siteName}] 控制台: ${msg.text()}`);
        });
        
        page.on('pageerror', error => {
            console.log(`[${siteName}] 页面错误: ${error.message}`);
        });
        
        // 导航到站点
        console.log(`[${siteName}] 正在访问站点...`);
        await page.goto(url, { waitUntil: 'networkidle' });
        
        // 等待页面加载
        await page.waitForTimeout(5000);
        
        // 检查页面标题
        const title = await page.title();
        console.log(`[${siteName}] 页面标题: ${title}`);
        
        // 检查是否存在登录表单
        const loginForm = await page.$('form');
        if (loginForm) {
            console.log(`[${siteName}] 检测到登录表单`);
            
            // 尝试登录（使用测试账户）
            try {
                await page.fill('[id="email"]', 'saiter2306001@163.com');
                await page.fill('[id="password"]', 'hsai1234');
                await page.click('button[type="submit"]');
                console.log(`[${siteName}] 已提交登录表单`);
                
                // 等待登录完成
                await page.waitForTimeout(3000);
            } catch (error) {
                console.log(`[${siteName}] 登录过程出错: ${error.message}`);
            }
        }
        
        // 检查WebSocket连接
        console.log(`[${siteName}] 检查WebSocket连接...`);
        
        // 在页面上执行JavaScript来检查WebSocket状态
        const wsCheckResult = await page.evaluate(() => {
            // 检查是否存在Socket.IO连接
            if (typeof io !== 'undefined') {
                return {
                    socketIO: true,
                    message: 'Socket.IO库已加载'
                };
            }
            
            // 检查全局WebSocket对象
            if (typeof WebSocket !== 'undefined') {
                return {
                    webSocket: true,
                    message: 'WebSocket API可用'
                };
            }
            
            return {
                socketIO: false,
                webSocket: false,
                message: '未检测到WebSocket相关库'
            };
        });
        
        console.log(`[${siteName}] WebSocket检查结果:`, wsCheckResult);
        
        // 尝试建立WebSocket连接并发送测试消息
        console.log(`[${siteName}] 尝试建立WebSocket连接...`);
        const wsTestResult = await page.evaluate(async () => {
            try {
                // 这里需要根据实际的WebSocket连接方式来测试
                // 假设使用Socket.IO
                if (typeof io !== 'undefined') {
                    // 获取当前页面的主机名和端口
                    const baseUrl = window.location.origin.replace(':5173', ':8080').replace(':5174', ':8080');
                    
                    return new Promise((resolve) => {
                        const socket = io(baseUrl, {
                            path: '/ws/socket.io',
                            transports: ['websocket', 'polling'],
                            timeout: 10000
                        });
                        
                        socket.on('connect', () => {
                            resolve({
                                success: true,
                                message: 'WebSocket连接成功',
                                socketId: socket.id
                            });
                        });
                        
                        socket.on('connect_error', (error) => {
                            resolve({
                                success: false,
                                message: 'WebSocket连接错误: ' + error.message
                            });
                        });
                        
                        socket.on('disconnect', (reason) => {
                            console.log('WebSocket断开连接:', reason);
                        });
                        
                        // 监听HSAI相关事件
                        socket.on('hsai_response', (data) => {
                            console.log('收到hsai_response:', data);
                        });
                        
                        socket.on('hsai_error', (data) => {
                            console.log('收到hsai_error:', data);
                        });
                        
                        // 5秒后超时
                        setTimeout(() => {
                            resolve({
                                success: false,
                                message: 'WebSocket连接超时'
                            });
                        }, 5000);
                    });
                } else {
                    return {
                        success: false,
                        message: 'Socket.IO库未加载'
                    };
                }
            } catch (error) {
                return {
                    success: false,
                    message: 'WebSocket测试出错: ' + error.message
                };
            }
        });
        
        console.log(`[${siteName}] WebSocket测试结果:`, wsTestResult);
        
        // 等待一段时间观察结果
        await page.waitForTimeout(10000);
        
    } catch (error) {
        console.log(`[${siteName}] 测试过程中出错: ${error.message}`);
    } finally {
        await browser.close();
    }
}

async function main() {
    console.log('开始分析两个前端站点的WebSocket连接问题');
    
    // 分别分析两个站点
    await analyzeSite('http://192.168.20.62:5173', '站点1');
    await analyzeSite('http://192.168.20.62:5174', '站点2');
    
    console.log('\n分析完成');
}

// 运行主函数
main().catch(console.error);