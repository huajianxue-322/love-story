#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
deploy.py — 用 GitHub API 部署 index.html 到线上（绕过 Pages 部署分支保护）
用法: python deploy.py [要部署的文件]
默认部署 love/index.html
"""
import base64, json, os, sys, urllib.request

TOKEN = os.environ.get("LOVE_GITHUB_TOKEN", "").strip()
if not TOKEN:
    sys.exit("请先设置环境变量 LOVE_GITHUB_TOKEN")
OWNER, REPO = "huajianxue-322", "love-story"
FILE = sys.argv[1] if len(sys.argv) > 1 else "index.html"
API = f"https://api.github.com/repos/{OWNER}/{REPO}/contents/{FILE}"

def api(url, method="GET", body=None):
    req = urllib.request.Request(url, method=method)
    req.add_header("Authorization", "Bearer " + TOKEN)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    data = json.dumps(body).encode("utf-8") if body else None
    try:
        with urllib.request.urlopen(req, data) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return {"_error": e.code, "_msg": e.read().decode("utf-8")[:300]}

with open(FILE, "rb") as f:
    content = base64.b64encode(f.read()).decode("ascii")

sha = api(API).get("sha")
print("线上当前 sha:", sha)

body = {"message": "deploy site update", "content": content}
if sha:
    body["sha"] = sha

res = api(API, "PUT", body)
if "content" in res:
    print("部署成功 ✓ 新 sha:", res["content"]["sha"][:10])
else:
    print("部署失败 ✗", res.get("_error"), res.get("_msg", ""))
