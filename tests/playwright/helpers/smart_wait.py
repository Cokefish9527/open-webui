"""
智能等待工具类，用于优化Playwright的元素等待逻辑
避免固定超时时间导致的问题
"""

import asyncio
import time
from typing import Callable, Any, Optional
from playwright.sync_api import Page, Locator


async def wait_for_element_visible(
    locator: Locator,
    max_wait_time: float = 60.0,
    poll_interval: float = 0.5
) -> bool:
    """
    智能等待元素可见
    
    Args:
        locator: Playwright定位器对象
        max_wait_time: 最大等待时间（秒）
        poll_interval: 轮询间隔（秒）
    
    Returns:
        bool: 元素是否可见
    """
    start_time = time.time()
    while time.time() - start_time < max_wait_time:
        try:
            # 检查元素是否存在且可见
            if await locator.is_visible():
                return True
        except Exception:
            # 元素可能还不存在，继续等待
            pass
        
        # 等待下一个轮询周期
        await asyncio.sleep(poll_interval)
    
    # 超时后再次检查一次
    try:
        return await locator.is_visible()
    except Exception:
        return False


async def wait_for_element_enabled(
    locator: Locator,
    max_wait_time: float = 30.0,
    poll_interval: float = 0.5
) -> bool:
    """
    智能等待元素启用（可点击/可交互）
    
    Args:
        locator: Playwright定位器对象
        max_wait_time: 最大等待时间（秒）
        poll_interval: 轮询间隔（秒）
    
    Returns:
        bool: 元素是否启用
    """
    start_time = time.time()
    while time.time() - start_time < max_wait_time:
        try:
            # 检查元素是否存在且启用
            if await locator.is_enabled():
                return True
        except Exception:
            # 元素可能还不存在，继续等待
            pass
        
        # 等待下一个轮询周期
        await asyncio.sleep(poll_interval)
    
    # 超时后再次检查一次
    try:
        return await locator.is_enabled()
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
    page: Page,
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
    page: Page,
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


async def wait_for_text_change(
    locator: Locator,
    initial_text: str,
    max_wait_time: float = 30.0,
    poll_interval: float = 0.5
) -> bool:
    """
    智能等待元素文本发生变化
    
    Args:
        locator: Playwright定位器对象
        initial_text: 初始文本
        max_wait_time: 最大等待时间（秒）
        poll_interval: 轮询间隔（秒）
    
    Returns:
        bool: 文本是否发生变化
    """
    start_time = time.time()
    while time.time() - start_time < max_wait_time:
        try:
            current_text = await locator.text_content()
            if current_text != initial_text:
                return True
        except Exception:
            # 元素可能还不存在，继续等待
            pass
        
        # 等待下一个轮询周期
        await asyncio.sleep(poll_interval)
    
    # 超时后再次检查一次
    try:
        current_text = await locator.text_content()
        return current_text != initial_text
    except Exception:
        return False


async def wait_for_element_count(
    page: Page,
    selector: str,
    expected_count: int,
    max_wait_time: float = 30.0,
    poll_interval: float = 0.5
) -> bool:
    """
    智能等待元素数量达到预期值
    
    Args:
        page: Playwright页面对象
        selector: 元素选择器
        expected_count: 期望的元素数量
        max_wait_time: 最大等待时间（秒）
        poll_interval: 轮询间隔（秒）
    
    Returns:
        bool: 元素数量是否达到预期值
    """
    start_time = time.time()
    while time.time() - start_time < max_wait_time:
        try:
            elements = page.locator(selector)
            count = await elements.count()
            if count >= expected_count:
                return True
        except Exception:
            # 元素可能还不存在，继续等待
            pass
        
        # 等待下一个轮询周期
        await asyncio.sleep(poll_interval)
    
    # 超时后再次检查一次
    try:
        elements = page.locator(selector)
        count = await elements.count()
        return count >= expected_count
    except Exception:
        return False