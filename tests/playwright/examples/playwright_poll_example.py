"""
PlayWright内置poll功能示例
展示如何使用expect.poll进行智能等待
"""

import asyncio
from playwright.async_api import async_playwright


async def wait_for_send_button_with_poll(page):
    """
    使用PlayWright的expect.poll等待发送按钮可用
    """
    try:
        # 使用expect.poll等待发送按钮变为可用
        # 这会轮询检查条件直到满足或超时
        await page.expect_poll(
            lambda: page.locator('#send-message-button').is_enabled(),
            timeout=30000  # 30秒超时
        ).to_be_true()
        return True
    except Exception:
        return False


async def wait_for_strategy_card_with_poll(page):
    """
    使用PlayWright的expect.poll等待策略卡片出现
    """
    # 策略卡片选择器列表
    strategy_card_selectors = [
        'div.relative.px-2.py-4.mb-4.border.border-gray-800.rounded-xl.border-dashed.bg-\\[\\#0e1322\\]',
        'div:has(img[src="/static/ai_strategic.png"])',
        'div[class*="strategy-card"]',
        '[data-testid="strategy-card"]',
        '.strategy-card',
        'div:has([class*="strategy"]):has([class*="card"])',
    ]
    
    for selector in strategy_card_selectors:
        try:
            # 使用expect.poll等待策略卡片可见
            await page.expect_poll(
                lambda: page.locator(selector).first.is_visible(),
                timeout=10000  # 10秒超时
            ).to_be_true()
            return True, selector
        except Exception:
            # 继续尝试下一个选择器
            continue
    
    return False, None


async def example_with_playwright_poll():
    """
    使用PlayWright内置poll功能的示例
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        # 导航到页面
        await page.goto("http://localhost:8080")
        
        # 使用PlayWright的poll功能等待发送按钮可用
        send_button_available = await wait_for_send_button_with_poll(page)
        
        if send_button_available:
            print("发送按钮已变为可用")
        else:
            print("等待发送按钮超时")
        
        # 使用PlayWright的poll功能等待策略卡片出现
        card_found, selector = await wait_for_strategy_card_with_poll(page)
        
        if card_found:
            print(f"策略卡片已出现，使用选择器: {selector}")
        else:
            print("等待策略卡片超时，未找到卡片")
        
        await browser.close()


async def main():
    print("=== 使用PlayWright内置poll功能的示例 ===")
    await example_with_playwright_poll()


if __name__ == "__main__":
    asyncio.run(main())