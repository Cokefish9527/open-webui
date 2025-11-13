import asyncio
from playwright.async_api import async_playwright
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def analyze_site(url, site_name):
    logger.info(f"\n=== 分析 {site_name} ({url}) ===")
    
    async with async_playwright() as p:
        # 启动浏览器（非无头模式以便观察）
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            # 启用控制台日志捕获
            page.on("console", lambda msg: logger.info(f"[{site_name}] 控制台: {msg.text}"))
            page.on("pageerror", lambda error: logger.info(f"[{site_name}] 页面错误: {error}"))
            
            # 导航到站点
            logger.info(f"[{site_name}] 正在访问站点...")
            await page.goto(url, wait_until="networkidle")
            
            # 等待页面加载
            await page.wait_for_timeout(5000)
            
            # 检查页面标题
            title = await page.title()
            logger.info(f"[{site_name}] 页面标题: {title}")
            
            # 检查是否存在登录表单
            login_form = await page.query_selector("form")
            if login_form:
                logger.info(f"[{site_name}] 检测到登录表单")
                
                # 尝试登录（使用测试账户）
                try:
                    await page.fill('[id="email"]', 'saiter2306001@163.com')
                    await page.fill('[id="password"]', '123456')
                    await page.click('button[type="submit"]')
                    logger.info(f"[{site_name}] 已提交登录表单")
                    
                    # 等待登录完成
                    await page.wait_for_timeout(3000)
                except Exception as error:
                    logger.info(f"[{site_name}] 登录过程出错: {error}")
            
            # 检查WebSocket连接
            logger.info(f"[{site_name}] 检查WebSocket连接...")
            
            # 等待页面完全加载并建立WebSocket连接
            await page.wait_for_timeout(5000)
            
            # 在页面上执行JavaScript来检查WebSocket状态
            ws_check_result = await page.evaluate("""() => {
                console.log('检查Socket.IO库...');
                console.log('io:', typeof io);
                console.log('WebSocket:', typeof WebSocket);
                
                // 检查是否存在Socket.IO连接
                if (typeof io !== 'undefined') {
                    console.log('Socket.IO版本:', io.version);
                    return {
                        socketIO: true,
                        message: 'Socket.IO库已加载',
                        version: typeof io.version !== 'undefined' ? io.version : '未知版本'
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
            }""")
            
            logger.info(f"[{site_name}] WebSocket检查结果: {ws_check_result}")
            
            # 尝试建立WebSocket连接并发送测试消息
            logger.info(f"[{site_name}] 尝试建立WebSocket连接并发送测试消息...")
            ws_test_result = await page.evaluate("""async () => {
                try {
                    console.log('开始WebSocket连接测试...');
                    
                    // 检查Socket.IO是否真的存在
                    if (typeof io === 'undefined') {
                        console.log('Socket.IO库未定义');
                        return {
                            success: false,
                            message: 'Socket.IO库未加载'
                        };
                    }
                    
                    // 获取当前页面的主机名和端口
                    const baseUrl = window.location.origin;
                    const wsUrl = baseUrl.replace(':5173', ':8080').replace(':5174', ':8080');
                    
                    console.log('尝试连接到WebSocket服务器:', wsUrl);
                    
                    // 检查io是否是函数
                    console.log('io类型:', typeof io);
                    console.log('io内容:', io);
                    
                    return new Promise((resolve) => {
                        // 使用正确的Socket.IO连接方式
                        const socket = io(wsUrl, {
                            path: '/ws/socket.io',
                            transports: ['websocket', 'polling'],
                            timeout: 10000,
                            reconnection: true,
                            reconnectionDelay: 1000,
                            reconnectionDelayMax: 5000,
                            randomizationFactor: 0.5
                        });
                        
                        socket.on('connect', () => {
                            console.log('WebSocket连接成功, socket ID:', socket.id);
                            // 发送测试消息
                            socket.emit('message', {
                                type: 'welcome',
                                content: '测试连接消息'
                            });
                            
                            resolve({
                                success: true,
                                message: 'WebSocket连接成功',
                                socketId: socket.id
                            });
                        });
                        
                        socket.on('connect_error', (error) => {
                            console.log('WebSocket连接错误:', error);
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
                        
                        // 10秒后超时
                        setTimeout(() => {
                            resolve({
                                success: false,
                                message: 'WebSocket连接超时'
                            });
                        }, 10000);
                    });
                } catch (error) {
                    console.log('WebSocket测试出错:', error);
                    return {
                        success: false,
                        message: 'WebSocket测试出错: ' + error.message
                    };
                }
            }""")
            
            logger.info(f"[{site_name}] WebSocket测试结果: {ws_test_result}")
            
            # 等待一段时间观察结果
            await page.wait_for_timeout(10000)
            
        except Exception as error:
            logger.info(f"[{site_name}] 测试过程中出错: {error}")
            import traceback
            logger.info(f"[{site_name}] 错误详情: {traceback.format_exc()}")
        finally:
            await browser.close()

async def main():
    logger.info("开始分析两个前端站点的WebSocket连接问题")
    
    # 分别分析两个站点
    await analyze_site('http://192.168.20.62:5173', '站点1')
    await analyze_site('http://192.168.20.62:5174', '站点2')
    
    logger.info('\n分析完成')

if __name__ == "__main__":
    asyncio.run(main())