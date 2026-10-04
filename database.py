import os
import json
import csv
import io
import base64
import urllib.request
import streamlit as st

# --- PROFILE & PROGRESS TRACKER FUNCTIONS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Check if we are running locally (via .env) or on Streamlit Cloud
IS_LOCAL = os.path.exists(os.path.join(BASE_DIR, ".env")) or os.getenv("APP_ENV") == "dev"

if IS_LOCAL:
    PROFILE_FILE = os.path.join(BASE_DIR, "profile_dev.json")
    print("🛠️ Running in DEV mode (local files)")
else:
    PROFILE_FILE = os.path.join(BASE_DIR, "profile.json")
    print("🚀 Running in PROD mode (live GitHub files)")

GITHUB_REPO = "MelTaz/Leonardo-Study-Engine"
GITHUB_BRANCH = "data"

def get_github_token():
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        try:
            token = st.secrets.get("GITHUB_TOKEN")
        except Exception:
            token = None
    return token

def load_profile_from_github(token=None) -> dict:
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/profile.json?ref={GITHUB_BRANCH}"
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "Leonardo-Study-Engine"
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            content_b64 = data.get("content", "")
            json_text = base64.b64decode(content_b64).decode('utf-8-sig')
            parsed = json.loads(json_text)
            if "summary" not in parsed:
                return {"summary": parsed, "history": []}
            return parsed
    except Exception:
        return None

def generate_history_csv(profile_data: dict) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Date", "Topic", "Difficulty", "Score", "Total", "Accuracy %", "Mistakes Count", "Missed Questions Summary"])
    for log in reversed(profile_data.get("history", [])):
        tot = log.get("total", 0)
        sc = log.get("score", 0)
        acc = f"{int((sc / tot) * 100)}%" if tot > 0 else "0%"
        m = log.get("mistakes", [])
        m_sum = "; ".join([f"{item.get('question', '')} [Selected: {item.get('selected', '')}, Correct: {item.get('correct', '')}]" for item in m])
        writer.writerow([
            log.get("date", ""),
            log.get("topic", ""),
            log.get("difficulty", ""),
            sc,
            tot,
            acc,
            len(m),
            m_sum
        ])
    return output.getvalue()

def save_profile_to_github_squashed(token: str, profile_data: dict) -> bool:
    if not token:
        return False
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "Leonardo-Study-Engine",
        "Content-Type": "application/json"
    }
    try:
        # 1. Create blob for profile.json
        json_str = json.dumps(profile_data, indent=4)
        req = urllib.request.Request(
            f"https://api.github.com/repos/{GITHUB_REPO}/git/blobs",
            data=json.dumps({"content": json_str, "encoding": "utf-8"}).encode('utf-8'),
            headers=headers,
            method="POST"
        )
        with urllib.request.urlopen(req) as resp:
            json_blob_sha = json.loads(resp.read().decode('utf-8'))["sha"]
            
        # 2. Create blob for profile_history.csv
        csv_str = generate_history_csv(profile_data)
        req = urllib.request.Request(
            f"https://api.github.com/repos/{GITHUB_REPO}/git/blobs",
            data=json.dumps({"content": csv_str, "encoding": "utf-8"}).encode('utf-8'),
            headers=headers,
            method="POST"
        )
        with urllib.request.urlopen(req) as resp:
            csv_blob_sha = json.loads(resp.read().decode('utf-8'))["sha"]
            
        # 3. Create tree containing both blobs
        tree_payload = {
            "tree": [
                {"path": "profile.json", "mode": "100644", "type": "blob", "sha": json_blob_sha},
                {"path": "profile_history.csv", "mode": "100644", "type": "blob", "sha": csv_blob_sha}
            ]
        }
        req = urllib.request.Request(
            f"https://api.github.com/repos/{GITHUB_REPO}/git/trees",
            data=json.dumps(tree_payload).encode('utf-8'),
            headers=headers,
            method="POST"
        )
        with urllib.request.urlopen(req) as resp:
            tree_sha = json.loads(resp.read().decode('utf-8'))["sha"]
            
        # 4. Create standalone commit with no parents (permanently squashed!)
        commit_payload = {
            "message": "Update study profile [skip ci]",
            "tree": tree_sha,
            "parents": []
        }
        req = urllib.request.Request(
            f"https://api.github.com/repos/{GITHUB_REPO}/git/commits",
            data=json.dumps(commit_payload).encode('utf-8'),
            headers=headers,
            method="POST"
        )
        with urllib.request.urlopen(req) as resp:
            new_commit_sha = json.loads(resp.read().decode('utf-8'))["sha"]
            
        # 5. Force update refs/heads/data to point to new commit
        ref_payload = {
            "sha": new_commit_sha,
            "force": True
        }
        req = urllib.request.Request(
            f"https://api.github.com/repos/{GITHUB_REPO}/git/refs/heads/{GITHUB_BRANCH}",
            data=json.dumps(ref_payload).encode('utf-8'),
            headers=headers,
            method="PATCH"
        )
        with urllib.request.urlopen(req) as resp:
            return True
    except Exception as e:
        print(f"Error saving to GitHub: {e}")
        return False

def load_profile():
    # Only fetch from GitHub if we are in PROD mode
    if not IS_LOCAL:
        token = get_github_token()
        cloud_data = load_profile_from_github(token)
        if cloud_data is not None:
            try:
                with open(PROFILE_FILE, "w", encoding="utf-8") as f:
                    json.dump(cloud_data, f, indent=4)
            except Exception:
                pass
            return cloud_data
        
    if os.path.exists(PROFILE_FILE):
        try:
            with open(PROFILE_FILE, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
                if "summary" not in data:
                    return {"summary": data, "history": []}
                return data
        except Exception:
            return {"summary": {}, "history": []}
    return {"summary": {}, "history": []}

def save_profile(profile):
    try:
        with open(PROFILE_FILE, "w", encoding="utf-8") as f:
            json.dump(profile, f, indent=4)
    except Exception:
        pass
        
    # Only push to GitHub if we are in PROD mode
    if not IS_LOCAL:
        token = get_github_token()
        if token:
            save_profile_to_github_squashed(token, profile)

