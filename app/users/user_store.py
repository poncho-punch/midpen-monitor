import json
import os
from datetime import datetime
from typing import List, Optional

def load_users() -> List[dict]:
    import logging
    logger = logging.getLogger("users.user_store")
    env = os.environ.get("ALERT_ENV", "PROD").upper()
    if env == "DEV":
        users_file = "users.dev.json"
    else:
        users_file = "users.json"
    # Use /app/app/users/data for persistent user files
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    os.makedirs(data_dir, exist_ok=True)
    USERS_PATH = os.path.join(data_dir, users_file)
    logger.info(f"[UserStore] Loading users from: {USERS_PATH}")
    if not os.path.exists(USERS_PATH):
        logger.warning(f"[UserStore] User file not found: {USERS_PATH}")
        print(f"\n[WARNING] User file not found: {USERS_PATH}\n"
              f"Please create this file with your user/contact info.\n"
              f"You can copy app/users/{users_file.replace('.json', '.example.json')} as a template.\n")
        return []
    with open(USERS_PATH, 'r') as f:
        try:
            users = json.load(f)
            logger.info(f"[UserStore] Loaded {len(users)} users from {USERS_PATH}")
            return users
        except Exception as e:
            logger.error(f"[UserStore] Failed to load users from {USERS_PATH}: {e}")
            return []

def save_users(users: List[dict]):
    with open(USERS_PATH, 'w') as f:
        json.dump(users, f, indent=2)

def find_user(email: str) -> Optional[dict]:
    users = load_users()
    for user in users:
        if user['id'] == email:
            return user
    return None

def add_or_update_user(email: str, phone: Optional[str], zones: List[str]):
    users = load_users()
    now = datetime.utcnow().isoformat() + 'Z'
    for user in users:
        if user['id'] == email:
            user['phone'] = phone
            user['zones'] = zones
            return save_users(users)
    users.append({
        'id': email,
        'email': email,
        'phone': phone,
        'zones': zones,
        'created_at': now
    })
    save_users(users)

def remove_user(email: str):
    users = load_users()
    users = [u for u in users if u['id'] != email]
    save_users(users)
