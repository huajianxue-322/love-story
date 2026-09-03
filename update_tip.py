#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
update_tip.py — 把一条水彩技巧追加到云端 love-data/tips.json（网页「水彩小课堂」自动显示）
用法: python update_tip.py "技巧内容"

钥匙获取顺序（任选其一即可）：
  1. 环境变量 LOVE_GITHUB_TOKEN
  2. 本地文件 %LOCALAPPDATA%\\hermes\\love_token.txt
  3. gh CLI 登录态 (gh auth token)
"""
import base64, datetime, json, os, subprocess, sys, urllib.request, urllib.error, time

OWNER, REPO = "huajianxue-322", "love-story"
API = f"https://api.github.com/repos/{OWNER}/{REPO}/contents/love-data%2Ftips.json"

def get_token():
    t = os.environ.get("LOVE_GITHUB_TOKEN", "").strip()
    if t:
        return t
    tf = os.path.join(os.environ.get("LOCALAPPDATA", ""), "hermes", "love_token.txt")
    if os.path.exists(tf):
        t = open(tf, encoding="utf-8").read().strip()
        if t:
            return t
    try:
        r = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, timeout=20)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    except Exception:
        pass
    return ""

def api(method="GET", body=None):
    req = urllib.request.Request(API, method=method)
    req.add_header("Authorization", "Bearer " + TOKEN)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    data = json.dumps(body).encode() if body else None
    try:
        with urllib.request.urlopen(req, data) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return {"_error": e.code, "_msg": e.read().decode()[:200]}

if __name__ == "__main__":
    TOKEN = get_token()
    if not TOKEN:
        sys.exit("错误: 找不到钥匙 (env LOVE_GITHUB_TOKEN / love_token.txt / gh auth)")
    tip = " ".join(sys.argv[1:]).strip()
    if not tip:
        sys.exit("用法: python update_tip.py \"技巧内容\"")
    date = datetime.date.today().isoformat()
    for attempt in range(3):
        d = api()
        if "_error" in d:
            sys.exit(f"读取 tips.json 失败: {d.get('_error')}")
        data = json.loads(base64.b64decode(d["content"]).decode())
        data.setdefault("tips", [])
        data["tips"].append({"date": date, "tip": tip})
        body = {
            "message": f"add watercolor tip {date}",
            "content": base64.b64encode(json.dumps(data, ensure_ascii=False).encode()).decode(),
            "sha": d["sha"],
        }
        r = api("PUT", body)
        if "content" in r:
            print(f"✓ 已推送技巧（第 {len(data['tips'])} 条）：{tip[:40]}…")
            sys.exit(0)
        if r.get("_error") == 409 and attempt < 2:
            time.sleep(2)
            continue
        sys.exit(f"推送失败: {r.get('_error')} {r.get('_msg')}")
