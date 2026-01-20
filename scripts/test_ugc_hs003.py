import requests
import sys
import json
import os

# --- Configuration ---
# Target Server
BASE_URL = os.getenv("OPEN_WEBUI_BASE_URL", "http://localhost:8080")
# Auth Credentials (User must be the owner of the task)
EMAIL = os.getenv("OPEN_WEBUI_EMAIL", "admin@hsai.cc")
PASSWORD = os.getenv("OPEN_WEBUI_PASSWORD", "admin")
# Target Task ID
TASK_ID = "YOUR_TASK_ID_HERE"  # <--- REPLACE THIS or pass as arg

def login(email, password):
    print(f"Logging in as {email}...")
    url = f"{BASE_URL}/api/v1/auths/signin"
    try:
        resp = requests.post(url, json={"email": email, "password": password})
        resp.raise_for_status()
        data = resp.json()
        return data["token"]
    except Exception as e:
        print(f"Login failed: {e}")
        if resp:
            print(f"Response: {resp.text}")
        sys.exit(1)

def trigger_hs003(token, task_id):
    print(f"Triggering HS003 (Generate Video) for Task {task_id}...")
    url = f"{BASE_URL}/api/v1/ugc/tasks/{task_id}/generate_video"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Optional: Provide scene edits if needed
    # payload = [{"scene_index": 0, "subtitle": "Edited subtitle"}] 
    payload = [] 

    try:
        resp = requests.post(url, json=payload, headers=headers)
        if resp.status_code == 200:
            print("\nSUCCESS: HS003 triggered successfully.")
            print("Response Data:")
            print(json.dumps(resp.json(), indent=2, ensure_ascii=False))
        else:
            print(f"\nFAILED: Status Code {resp.status_code}")
            print("Response Error:")
            try:
                print(json.dumps(resp.json(), indent=2, ensure_ascii=False))
            except:
                print(resp.text)
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    # Allow passing task_id as command line argument
    if len(sys.argv) > 1:
        TASK_ID = sys.argv[1]
    
    if TASK_ID == "YOUR_TASK_ID_HERE":
        print("Error: Please set TASK_ID in the script or pass it as an argument.")
        print("Usage: python test_ugc_hs003.py <task_id>")
        sys.exit(1)

    auth_token = login(EMAIL, PASSWORD)
    trigger_hs003(auth_token, TASK_ID)
