#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script: Listen to Redis queue for messages
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
from typing import Tuple, Any

def get_redis_client():
    """Get Redis client instance"""
    return redis.from_url(REDIS_URL)

def listen_to_queue():
    """Listen to Redis queue for messages"""
    try:
        # Get Redis client
        redis_client = get_redis_client()
        queue_name = "ai-conversation-agent-message-queue"
        
        print(f"Listening to queue: {queue_name}")
        print("Press Ctrl+C to stop")
        print("-" * 50)
        
        while True:
            # Blocking pop from queue with 5 second timeout
            result = redis_client.brpop([queue_name], timeout=5)
            
            if result:
                # Parse message
                if isinstance(result, (list, tuple)) and len(result) >= 2:
                    queue, message_data = result[0], result[1]
                    message = json.loads(message_data.decode('utf-8'))
                    
                    print("Received message:")
                    print(f"  Session ID: {message.get('session_id', 'N/A')}")
                    print(f"  User ID: {message.get('user_id', 'N/A')}")
                    print(f"  Socket ID: {message.get('socket_id', 'N/A')}")
                    print(f"  Status: {message.get('status', 'N/A')}")
                    print(f"  Content type: {message.get('content_type', 'N/A')}")
                    if 'content' in message and 'data' in message['content']:
                        content_length = len(message['content']['data'])
                        print(f"  Content length: {content_length} characters")
                    print("-" * 50)
                else:
                    print(f"Received unexpected message format: {result}")
                
    except KeyboardInterrupt:
        print("\nStopping listener")
    except Exception as e:
        print(f"Error listening to queue: {e}")

if __name__ == "__main__":
    listen_to_queue()