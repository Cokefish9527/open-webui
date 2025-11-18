"""
高级Playwright智能等待示例
展示如何使用PlayWright的异步特性和自定义轮询策略
"""

import asyncio
import time
from playwright.async_api import async_playwright
from typing import Callable, Any, Optional


async def wait_for_element_visible(
    page,
    selector: str,
    max_wait_time: float = 60.0,
    poll_interval: float = 0.5
) -> bool:
    """
    智能等待元素可见
    
    Args:
        page: Playwright页面对象
        selector: 元素选择器
        max_wait_time: 最大等待时间（秒）
        poll_interval: 轮询间隔（秒）
    
    Returns:
        bool: 元素是否可见
    """
    start_time = time.time()
    while time.time() - start_time < max_wait_time:
        try:
            # 检查元素是否存在且可见
            element = page.locator(selector)
            if await element.is_visible():
                return True
        except Exception:
            # 元素可能还不存在，继续等待
            pass
        
        # 等待下一个轮询周期
        await asyncio.sleep(poll_interval)
    
    # 超时后再次检查一次
    try:
        element = page.locator(selector)
        return await element.is_visible()
    except Exception:
        return False


async def wait_for_element_enabled(
    page,
    selector: str,
    max_wait_time: float = 30.0,
    poll_interval: float = 0.5
) -> bool:
    """
    智能等待元素启用（可点击/可交互）
    
    Args:
        page: Playwright页面对象
        selector: 元素选择器
        max_wait_time: 最大等待时间（秒）
        poll_interval: 轮询间隔（秒）
    
    Returns:
        bool: 元素是否启用
    """
    start_time = time.time()
    while time.time() - start_time < max_wait_time:
        try:
            # 检查元素是否存在且启用
            element = page.locator(selector)
            if await element.is_enabled():
                return True
        except Exception:
            # 元素可能还不存在，继续等待
            pass
        
        # 等待下一个轮询周期
        await asyncio.sleep(poll_interval)
    
    # 超时后再次检查一次
    try:
        element = page.locator(selector)
        return await element.is_enabled()
    except Exception:
        return False


async def wait_for_condition(
    condition_func: Callable[[], Any],
    max_wait_time: float = 60.0,
    poll_interval: float = 0.5
) -> bool:
    """
    智能等待自定义条件满足
    
    Args:
        condition_func: 条件检查函数，返回True表示条件满足
        max_wait_time: 最大等待时间（秒）
        poll_interval: 轮询间隔（秒）
    
    Returns:
        bool: 条件是否满足
    """
    start_time = time.time()
    while time.time() - start_time < max_wait_time:
        try:
            # 检查条件是否满足
            if condition_func():
                return True
        except Exception:
            # 条件检查可能失败，继续等待
            pass
        
        # 等待下一个轮询周期
        await asyncio.sleep(poll_interval)
    
    # 超时后再次检查一次
    try:
        return condition_func()
    except Exception:
        return False


async def wait_for_send_button_available(
    page,
    max_wait_time: float = 30.0,
    poll_interval: float = 0.5
) -> bool:
    """
    智能等待发送按钮可用
    
    Args:
        page: Playwright页面对象
        max_wait_time: 最大等待时间（秒）
        poll_interval: 轮询间隔（秒）
    
    Returns:
        bool: 发送按钮是否可用
    """
    send_button = page.locator('#send-message-button')
    start_time = time.time()
    
    while time.time() - start_time < max_wait_time:
        try:
            # 检查发送按钮是否存在且启用（不禁用）
            if await send_button.is_enabled() and not (await send_button.is_disabled()):
                return True
        except Exception:
            # 按钮可能还不存在，继续等待
            pass
        
        # 等待下一个轮询周期
        await asyncio.sleep(poll_interval)
    
    # 超时后再次检查一次
    try:
        return await send_button.is_enabled() and not (await send_button.is_disabled())
    except Exception:
        return False


async def wait_for_strategy_card_visible(
    page,
    max_wait_time: float = 60.0,
    poll_interval: float = 1.0
) -> tuple[bool, Optional[str]]:
    """
    智能等待策略卡片出现
    
    Args:
        page: Playwright页面对象
        max_wait_time: 最大等待时间（秒）
        poll_interval: 轮询间隔（秒）
    
    Returns:
        tuple[bool, Optional[str]]: (是否找到卡片, 使用的选择器)
    """
    # 策略卡片选择器列表，按优先级排序
    strategy_card_selectors = [
        # 基于提供的HTML结构的更精确选择器
        'div.relative.px-2.py-4.mb-4.border.border-gray-800.rounded-xl.border-dashed.bg-\\[\\#0e1322\\]',
        'div:has(img[src="/static/ai_strategic.png"])',
        'div[class*="strategy-card"]',
        '[data-testid="strategy-card"]',
        '.strategy-card',
        'div:has([class*="strategy"]):has([class*="card"])',
    ]
    
    start_time = time.time()
    while time.time() - start_time < max_wait_time:
        # 尝试每个选择器
        for selector in strategy_card_selectors:
            try:
                strategy_card = page.locator(selector).first
                if await strategy_card.is_visible():
                    return True, selector
            except Exception:
                # 元素可能还不存在，继续尝试下一个选择器
                pass
        
        # 等待下一个轮询周期
        await asyncio.sleep(poll_interval)
    
    # 超时后再次检查一次
    for selector in strategy_card_selectors:
        try:
            strategy_card = page.locator(selector).first
            if await strategy_card.is_visible():
                return True, selector
        except Exception:
            continue
    
    return False, None


async def example_with_smart_wait():
    """
    使用智能等待的示例
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        # 导航到页面
        await page.goto("http://localhost:8080")
        
        # 智能等待发送按钮可用
        # 使用智能等待函数替代固定超时等待
        send_button_available = await wait_for_send_button_available(page, max_wait_time=30.0)
        
        if send_button_available:
            print("发送按钮已变为可用")
        else:
            print("等待发送按钮超时")
        
        # 智能等待策略卡片出现
        card_found, selector = await wait_for_strategy_card_visible(page, max_wait_time=60.0)
        
        if card_found:
            print(f"策略卡片已出现，使用选择器: {selector}")
        else:
            print("等待策略卡片超时，未找到卡片")
        
        await browser.close()


async def example_with_manual_smart_wait():
    """
    手动实现智能等待的示例
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        # 导航到页面
        await page.goto("http://localhost:8080")
        
        # 智能等待发送按钮可用 - 手动实现
        print("等待发送按钮变为可用...")
        send_button = page.locator('#send-message-button')
        send_button_available = False
        max_wait_time = 30.0  # 最大等待时间30秒
        poll_interval = 0.5   # 轮询间隔0.5秒
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            try:
                # 检查发送按钮是否存在且启用（不禁用）
                if await send_button.is_enabled() and not (await send_button.is_disabled()):
                    send_button_available = True
                    break
            except Exception:
                # 元素可能还不存在，继续等待
                pass
            
            # 等待下一个轮询周期
            await asyncio.sleep(poll_interval)
        
        if send_button_available:
            print("发送按钮已变为可用")
        else:
            print("等待发送按钮超时")
        
        # 智能等待策略卡片出现 - 手动实现
        print("检查策略卡片是否出现...")
        strategy_card_selectors = [
            'div.relative.px-2.py-4.mb-4.border.border-gray-800.rounded-xl.border-dashed.bg-\\[\\#0e1322\\]',
            'div:has(img[src="/static/ai_strategic.png"])',
            'div[class*="strategy-card"]',
            '[data-testid="strategy-card"]',
            '.strategy-card',
            'div:has([class*="strategy"]):has([class*="card"])',
        ]
        
        strategy_card_visible = False
        max_wait_time = 60.0  # 最大等待时间60秒
        poll_interval = 1.0   # 轮询间隔1秒
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time and not strategy_card_visible:
            for selector in strategy_card_selectors:
                try:
                    strategy_card = page.locator(selector).first
                    if await strategy_card.is_visible():
                        strategy_card_visible = True
                        print(f"找到策略卡片，使用选择器: {selector}")
                        break
                except Exception:
                    # 元素可能还不存在，继续尝试下一个选择器
                    pass
            
            if not strategy_card_visible:
                # 等待下一个轮询周期
                await asyncio.sleep(poll_interval)
        
        if not strategy_card_visible:
            print("检查策略卡片超时，未找到策略卡片")
        
        await browser.close()


async def main():
    print("=== 使用智能等待函数的示例 ===")
    await example_with_smart_wait()
    
    print("\n=== 手动实现智能等待的示例 ===")
    await example_with_manual_smart_wait()


if __name__ == "__main__":
    asyncio.run(main())