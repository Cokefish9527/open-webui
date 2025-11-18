"""
Playwright智能等待示例
展示如何使用智能轮询策略替代固定超时等待
"""

from playwright.sync_api import sync_playwright
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from helpers.smart_wait import wait_for_send_button_available, wait_for_strategy_card_visible
import asyncio


def example_with_smart_wait():
    """
    使用智能等待的示例
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        # 导航到页面
        page.goto("http://localhost:8080")
        
        # 智能等待发送按钮可用
        # 使用智能等待函数替代固定超时等待
        send_button_available = asyncio.run(
            wait_for_send_button_available(page, max_wait_time=30.0)
        )
        
        if send_button_available:
            print("发送按钮已变为可用")
        else:
            print("等待发送按钮超时")
        
        # 智能等待策略卡片出现
        card_found, selector = asyncio.run(
            wait_for_strategy_card_visible(page, max_wait_time=60.0)
        )
        
        if card_found:
            print(f"策略卡片已出现，使用选择器: {selector}")
        else:
            print("等待策略卡片超时，未找到卡片")
        
        browser.close()


def example_with_manual_smart_wait():
    """
    手动实现智能等待的示例
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        # 导航到页面
        page.goto("http://localhost:8080")
        
        # 智能等待发送按钮可用 - 手动实现
        print("等待发送按钮变为可用...")
        send_button = page.locator('#send-message-button')
        send_button_available = False
        max_wait_time = 30.0  # 最大等待时间30秒
        poll_interval = 0.5   # 轮询间隔0.5秒
        import time
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            try:
                # 检查发送按钮是否存在且启用（不禁用）
                if send_button.is_enabled() and not send_button.is_disabled():
                    send_button_available = True
                    break
            except Exception:
                # 元素可能还不存在，继续等待
                pass
            
            # 等待下一个轮询周期
            page.wait_for_timeout(int(poll_interval * 1000))
        
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
                    if strategy_card.is_visible():
                        strategy_card_visible = True
                        print(f"找到策略卡片，使用选择器: {selector}")
                        break
                except Exception:
                    # 元素可能还不存在，继续尝试下一个选择器
                    pass
            
            if not strategy_card_visible:
                # 等待下一个轮询周期
                page.wait_for_timeout(int(poll_interval * 1000))
        
        if not strategy_card_visible:
            print("检查策略卡片超时，未找到策略卡片")
        
        browser.close()


if __name__ == "__main__":
    print("=== 使用智能等待函数的示例 ===")
    example_with_smart_wait()
    
    print("\n=== 手动实现智能等待的示例 ===")
    example_with_manual_smart_wait()