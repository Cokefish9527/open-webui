#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script: Send a complete blueprint message with specified IDs to Redis queue
"""

import json
import sys
import os

# Add project path to Python path
project_root = os.path.join(os.path.dirname(__file__), '..')
backend_path = os.path.join(project_root, 'backend')
sys.path.insert(0, backend_path)

# Import REDIS_URL directly from the env.py file
env_file_path = os.path.join(backend_path, 'open_webui', 'env.py')

# Read the REDIS_URL from env.py
REDIS_URL = "redis://localhost:6379/0"  # Default value

try:
    with open(env_file_path, 'r', encoding='utf-8') as f:
        env_content = f.read()
        # Try to find REDIS_URL in the file
        import re
        redis_url_match = re.search(r'REDIS_URL\s*=\s*os\.environ\.get\([^,]+,\s*["\']([^"\']+)["\']\)', env_content)
        if redis_url_match:
            REDIS_URL = redis_url_match.group(1)
except Exception as e:
    print(f"Warning: Could not read REDIS_URL from env.py: {e}")

import redis

def get_redis_client():
    """Get Redis client instance"""
    return redis.from_url(REDIS_URL)

def send_blueprint_message():
    """Send blueprint message with specified IDs to Redis queue"""
    
    # Complete data with specified IDs
    message_data = {
        "env": "gray",
        "session_id": "23e45c2e-bf90-457a-8e04-c37b548e54aa",
        "user_id": "0086d2b1-1514-4450-8660-29629e27f984",
        "operate_id": "蓝图内容",
        "request_id": "66646e40-8156-4cdd-ba1b-7e3245f8358b",
        "socket_id": "4D99nArFPgwdM_ofAAAF",
        "status": "FINISHED",
        "content": {
            "data": "# AOK LED Light 出海视频获客战略蓝图 · Version 3.0  (更新版)\n\n> 依据企业官网 www.aokledlight.com 与已存档信息，结合最新海外短视频趋势，对 v2 版本进行全面升级。\n\n---\n## 1. 战略目标\n1. 时间周期：60 天（2 个月）\n2. 曝光目标：≥ 1,000,000 次（比 v2 提升 100%）\n3. 线索目标：≥ 400 条 B2B 潜在客户（比 v2 提升 100%）\n4. 品牌资产：沉淀 1 套可循环迭代的灯具评测内容库 + 60 条案例素材可长期复用。\n\n---\n## 2. 账号矩阵与发布计划\n| 平台 | 区域/语言 | 账号数量 | 日发量 | 60 天总发量 |\n|------|-----------|---------|--------|--------------|\n| TikTok | 美区 / 欧洲区 / 东南亚区 | 3 | 1/天 | 180 |\n| YouTube Shorts | 英文频道 / 西语频道 / 中文频道 | 3 | 1/天 | 180 |\n| LinkedIn | 公司主页 / 销售 #1 / 销售 #2 | 3 | 1/天 | 180 |\n| 合计 | — | **9** | **9/天** | **540** |\n\n*说明：每天 9 条短视频来自同一批素材的 AI 裂变，确保“原生但高效”。*\n\n---\n## 3. 素材需求估算\n1. AI 可将 1 组原片裂变 ≈ 3–5 条平台适配短视频。\n2. 540 条短视频 → 约需 120–150 组原片（安全冗余 20%）。\n3. 拍摄节奏：\n   • 每周拍摄 8 大场景 × 3 机位 ≈ 24 组原片 / 周。\n   • 60 天 ≈ 9 周，累计拍摄 ≈ 9 周 × 24 ≈ **216 组** 原片（含冗余）。\n4. 拍摄用时：集中拍摄 3 天即可完成 60% 以上原片，其余机动补拍。\n\n---\n## 4. 内容支柱 & 场景脚本\n1. 工厂探秘 (Factory Tour)  \n   • 镜头：SMT 贴片 → 老化测试 → 成品包装线 → 仓库自动立库  \n   • 钩子台词：Looking for a REAL LED factory? 60 seconds to find out!  \n   • 标题示例：60 秒走进 10,000㎡ AOK 工厂  \n   • BGM：电子工业氛围 Lo-Fi\n\n2. 产品测评 (Performance Test)  \n   • 镜头：Integrating Sphere 光效测试 → IP67 喷淋 → IK10 冲击演示  \n   • 钩子：Will your streetlight survive THIS test?  \n   • 标题：IP67 + IK10! 测试现场实拍  \n   • BGM：紧张 Tech Rock\n\n3. 客户案例 (Case Study)  \n   • 镜头：美西港口 800 套投光灯亮灯对比（航拍 + 地面）  \n   • 钩子：From 1000 W HPS → 400 W LED in 7 days  \n   • 标题：港口年省 120 万美元电费的秘密  \n   • BGM：史诗感 Orchestral\n\n4. 对比实验 (A/B Demo)  \n   • 镜头：旧 400 W HPS vs AOK 150 W UFO  12 m 高棚  \n   • 钩子：2 bulbs, same height – 50 % more lux, 60 % less power  \n   • 标题：工厂换灯 ROI 18 个月回本  \n   • BGM：科幻 Synthwave\n\n5. 安装指南 (How-to)  \n   • 镜头：开箱 → 接线 → 智能调光设定 (0-10 V & DALI)  \n   • 钩子：Can you install a 200 W high-bay in 90 seconds?  \n   • 标题：3 步安装，节省 40 % 人工  \n   • BGM：动感 Funk\n\n6. 行业科普 (LED 101)  \n   • 镜头：产品经理 + 动画解释 LM-80 / TM-21 / DLC Premium  \n   • 钩子：What does DLC Premium REALLY mean?  \n   • 标题：3 分钟教你看懂北美照明认证  \n   • BGM：轻快 Acoustic\n\n---\n## 5. 30 天滚动发布日历（示例首周）\n| 周期 | 周一 | 周二 | 周三 | 周四 | 周五 | 周六 | 周日 |\n|------|------|------|------|------|------|------|------|\n| 场景 | 工厂探秘 | 产品测评 | 客户案例 | 对比实验 | 安装指南 | 行业科普 | 高层访谈* |\n| 钩子 | Why choose China LED? | IP67 test — fail or pass? | 1 year ROI | HPS vs LED | 90 sec install | DLC 101 | CEO AMA |\n| 主播 | 员工 Vlog | 工程师 | KOL/客户 | 对比主持人 | 技术员 | 产品经理 | CEO |\n\n*高层访谈每两周 1 次，用于品牌背书与招募分销商。*\n\n---\n## 6. 人员与预算\n• 拍摄团队：2 人（手机 + 云台/无人机）；额外租 1 套补光灯 800 RMB/天  \n• 后期：CapCut Pro、Runway Gen-2、Descript → 订阅合计 ¥1,300 / 月  \n• 推广：TikTok Spark Ads、YouTube Discovery Ads 预算 ¥10,000  \n• 总预算控制：≤ ¥25,000 / 60 天  （含 20% 机动）\n\n---\n## 7. KPI 与数据追踪\n1. 曝光：累计浏览量 ≥ 1,000,000 ；播放完播率 ≥ 25 %\n2. 互动：点赞率 ≥ 4 %，评论 > 3,000，私信 ≥ 600\n3. 线索：表单 + 私信有效询盘 ≥ 400\n4. 跟踪工具：HubSpot + Google Looker Studio 自动看板，每日同步；TikTok Insight & YouTube Analytics API 与 CRM 对接。\n\n---\n## 8. 交付物 & 里程碑\n1. D+3 ：完成 216 组原片拍摄\n2. D+5 ：首批 50 条短视频（含三端封面）\n3. D+7 ：9 账号搭建 + 15 天内容库存入库\n4. D+30：阶段复盘 & 调整 AB 钩子脚本\n5. D+60：交付全量数据报告 + 下一周期规划\n\n---\n## 9. 下一步行动\n1. 核对并确认本蓝图（账号数量 / 目标 / 预算）。\n2. 确认后 → 立即创建拍摄清单 & 首批 30 条脚本。\n3. 如需调整，请备注修改点。\n\n> 请回复 \"确认蓝图\" 或指出需要修改的部分。确认后我将存档并进入脚本拆解阶段。"
        },
        "content_type": "blue_image_content",
        "create_ts": 1760326803832
    }
    
    try:
        # Get Redis client
        redis_client = get_redis_client()
        
        # Convert message to JSON and send to Redis queue
        queue_name = "ai-conversation-agent-message-queue"
        message_json = json.dumps(message_data, ensure_ascii=False)
        redis_client.lpush(queue_name, message_json)
        
        print("✓ Blueprint message successfully sent to Redis queue")
        print(f"  Queue name: {queue_name}")
        print(f"  Session ID: {message_data['session_id']}")
        print(f"  User ID: {message_data['user_id']}")
        print(f"  Socket ID: {message_data['socket_id']}")
        print(f"  Content length: {len(message_data['content']['data'])} characters")
        return True
        
    except Exception as e:
        print(f"✗ Failed to send blueprint message to Redis queue: {e}")
        return False

if __name__ == "__main__":
    print("Sending Blueprint Message to Redis Queue")
    print("=" * 50)
    send_blueprint_message()