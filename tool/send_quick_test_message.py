#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quick test script: Send a simple test message to Redis queue
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

def send_test_message(session_id=None, user_id=None, socket_id=None):
    """Send a simple test message to Redis queue"""
    
    # Default test data
    message_data = {
        "env": "test",
        "session_id": session_id or "test-session-id",
        "user_id": user_id or "test-user-id",
        "operate_id": "test_operation",
        "request_id": "test-request-id",
        "socket_id": socket_id or "test-socket-id",
        "status": "TEST",
        "content": {
            "data": "This is a test message"
        },
        "content_type": "test_content",
        "create_ts": 1234567890
    }
    
    try:
        # Get Redis client
        redis_client = get_redis_client()
        
        # Convert message to JSON and send to Redis queue
        queue_name = "ai-conversation-agent-message-queue"
        message_json = json.dumps(message_data, ensure_ascii=False)
        redis_client.lpush(queue_name, message_json)
        
        print("✓ Test message successfully sent to Redis queue")
        print(f"  Queue name: {queue_name}")
        print(f"  Session ID: {message_data['session_id']}")
        print(f"  User ID: {message_data['user_id']}")
        print(f"  Socket ID: {message_data['socket_id']}")
        return True
        
    except Exception as e:
        print(f"✗ Failed to send test message to Redis queue: {e}")
        return False

if __name__ == "__main__":
    print("Sending Quick Test Message to Redis Queue")
    print("=" * 50)
    
    # Parse command line arguments
    session_id = None
    user_id = None
    socket_id = None
    
    if len(sys.argv) > 1:
        session_id = sys.argv[1]
    if len(sys.argv) > 2:
        user_id = sys.argv[2]
    if len(sys.argv) > 3:
        socket_id = sys.argv[3]
    
    send_test_message(session_id, user_id, socket_id)