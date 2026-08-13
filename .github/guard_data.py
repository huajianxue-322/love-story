#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
云端守卫（GitHub Actions 定时运行）：
校验 love-data/data.json 的一致性，自动修复两类问题：
  1. 已删条目（墓碑标记）从集合中移除 —— 防止"删除的东西复活"
  2. 删除标记（deleted 数组）缺失或丢失 —— 防止墓碑被旧版页面覆盖清空
本脚本只做保守修复：仅删除被墓碑明确标记的条目，绝不碰其他数据。
"""
import base64, json, os, sys, time, urllib.request, urllib.error

OWNER, REPO = "huajianxue-322", "love-story"
TOKEN = os.environ.get("TOKEN", "")
API = f"https://api.github.com/repos/{OWNER}/{REPO}/contents/love-data%2Fdata.json"

# 与页面 SEED_TOMBSTONES 保持一致的历史遗留墓碑（可在此追加）
SEED_TOMBSTONES = [
    {"id": 92938, "type": "photos", "updatedAt": 1786604100000},
]

def api(method="GET", body=None, url=API):
    req = urllib.request.Request(url, method=method)
    req.add_header("Authorization", "Bearer " + TOKEN)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    data = json.dumps(body).encode() if body else None
    try:
        with urllib.request.urlopen(req, data) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return {"_error": e.code, "_msg": e.read().decode()[:200]}

def fix(data):
    """返回 (是否修复, 修复说明)"""
    changed = False
    msgs = []
    # 1. deleted 必须是数组
    if not isinstance(data.get("deleted"), list):
        data["deleted"] = []
        changed = True
        msgs.append("deleted 缺失，已重建")
    # 2. 种子墓碑必须在
    for s in SEED_TOMBSTONES:
        if not any(x.get("type") == s["type"] and x.get("id") == s["id"] for x in data["deleted"]):
            data["deleted"].append(dict(s))
            changed = True
            msgs.append(f"补种墓碑 {s['type']}:{s['id']}")
    # 3. 墓碑去重（type+id）
    seen, dedup = set(), []
    for x in data["deleted"]:
        k = f"{x.get('type')}_{x.get('id')}"
        if k not in seen:
            seen.add(k)
            dedup.append(x)
    if len(dedup) != len(data["deleted"]):
        data["deleted"] = dedup
        changed = True
        msgs.append("墓碑去重")
    # 4. 移除各集合中带墓碑标记的条目
    dead = {}
    for x in data["deleted"]:
        dead.setdefault(x.get("type"), set()).add(x.get("id"))
    for coll in ("timeline", "photos", "notes", "diary", "foods"):
        if not isinstance(data.get(coll), list):
            continue
        ids = dead.get(coll, set())
        kept = [x for x in data[coll] if x.get("id") not in ids]
        if len(kept) != len(data[coll]):
            removed = [x.get("id") for x in data[coll] if x.get("id") in ids]
            data[coll] = kept
            changed = True
            msgs.append(f"移除复活条目 {coll}: {removed}")
    return changed, msgs

def main():
    d = api()
    if "_error" in d:
        print(f"读取失败: {d.get('_error')} {d.get('_msg')}")
        sys.exit(1)
    data = json.loads(base64.b64decode(d["content"]).decode())
    changed, msgs = fix(data)
    if not changed:
        print("守卫检查通过，无需修复 ✓")
        return
    body = {
        "message": "guard: auto-fix resurrected items / missing tombstones",
        "content": base64.b64encode(json.dumps(data, ensure_ascii=False).encode()).decode(),
        "sha": d["sha"],
    }
    for attempt in range(3):
        r = api("PUT", body)
        if "content" in r:
            print("守卫已修复:")
            for m in msgs:
                print("  -", m)
            return
        if r.get("_error") == 409 and attempt < 2:
            time.sleep(2)
            d = api()
            data = json.loads(base64.b64decode(d["content"]).decode())
            body["sha"] = d["sha"]
            continue
        print(f"修复失败: {r.get('_error')} {r.get('_msg')}")
        sys.exit(1)

if __name__ == "__main__":
    main()
