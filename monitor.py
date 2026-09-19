#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SEVENTEEN × 泡泡玛特 发售信息监控脚本
功能：定时抓取目标页面，检测关键词命中，通过 wxpusher 推送微信通知
"""

import requests
import json
import time
import hashlib
import os
import sys
from datetime import datetime

# ============ 配置 ============
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
STATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state.json")
WXPUSHER_URL = "https://wxpusher.zjiecode.com/api/up/send-message"

# 请求头，模拟浏览器
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


def load_config():
    """读取配置文件"""
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_state():
    """读取运行状态（上次检测结果）"""
    if os.path.exists(STATE_PATH):
        try:
            with open(STATE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {"mode": "normal", "last_results": {}, "last_run": None}


def save_state(state):
    """保存运行状态到文件"""
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def fetch_page(url, timeout=30):
    """抓取页面 HTML 内容"""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        resp.raise_for_status()
        # 尝试自动检测编码
        if not resp.encoding or resp.encoding.lower() == "iso-8859-1":
            resp.encoding = resp.apparent_encoding
        return resp.text
    except requests.exceptions.RequestException as e:
        print(f"  [ERROR] 抓取失败: {e}")
        return None


def check_keywords(content, keywords):
    """检查内容中是否包含关键词，返回命中列表"""
    if not content:
        return []
    content_lower = content.lower()
    hits = []
    for kw in keywords:
        if kw.lower() in content_lower:
            hits.append(kw)
    return hits


def content_hash(content):
    """计算内容哈希，用于检测是否有变化"""
    if not content:
        return ""
    return hashlib.md5(content.encode("utf-8")).hexdigest()


def send_wxpusher(app_token, uids, title, content, url=None):
    """
    通过 wxpusher 推送消息到微信
    文档: https://wxpusher.zjiecode.com/docs/
    """
    payload = {
        "appToken": app_token,
        "content": content,
        "summary": title[:100],
        "contentType": 3,  # 3 = markdown
        "uids": uids,
    }
    if url:
        payload["url"] = url

    try:
        resp = requests.post(WXPUSHER_URL, json=payload, timeout=15)
        result = resp.json()
        if result.get("code") == 1000:
            print(f"  [PUSH] 推送成功")
            return True
        else:
            print(f"  [ERROR] 推送失败: {result}")
            return False
    except Exception as e:
        print(f"  [ERROR] 推送异常: {e}")
        return False


def run_one_round(config, state, app_token, uid):
    """执行一轮完整检查"""
    keywords = config["keywords"]
    sources = config["sources"]
    uids = [uid]
    new_hits = []

    for source in sources:
        name = source["name"]
        url = source["url"]
        print(f"\n  [CHECK] {name}")
        print(f"          {url}")

        content = fetch_page(url)
        if not content:
            continue

        hits = check_keywords(content, keywords)
        chash = content_hash(content)

        prev = state["last_results"].get(name, {})
        prev_hash = prev.get("hash", "")

        # 命中关键词，且内容跟上次不同 → 触发推送
        if hits and chash != prev_hash:
            new_hits.append({
                "source": name,
                "url": url,
                "hits": hits,
            })
            print(f"  🎯 命中: {', '.join(hits)}")
        elif hits:
            print(f"  ✓ 已命中，内容未变化（跳过推送）")
        else:
            print(f"  - 未命中关键词")

        # 更新状态
        state["last_results"][name] = {
            "hash": chash,
            "hits": hits,
            "checked_at": datetime.now().isoformat(),
        }

    # 有新命中 → 推送
    if new_hits:
        title = "🔔 SEVENTEEN × 泡泡玛特 发售信息更新！"
        parts = []
        for i, hit in enumerate(new_hits, 1):
            parts.append(f"### {i}. {hit['source']}")
            parts.append(f"**命中关键词**: {', '.join(hit['hits'])}")
            parts.append(f"**链接**: {hit['url']}")
            parts.append("")

        content = "\n".join(parts)
        push_url = new_hits[0]["url"]

        send_wxpusher(app_token, uids, title, content, push_url)

        # 首次命中 → 切换到预热模式
        if state["mode"] == "normal":
            state["mode"] = "preheat"
            print(f"\n  ⚡ 进入预热模式（后续频率加密）")

    return new_hits


def main():
    print("=" * 60)
    print(f"  SEVENTEEN × 泡泡玛特 监控启动")
    print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 读取配置和状态
    config = load_config()
    state = load_state()

    # 从环境变量读取 wxpusher 密钥
    app_token = os.environ.get("WXPUSHER_APP_TOKEN", "").strip()
    uid = os.environ.get("WXPUSHER_UID", "").strip()

    if not app_token or not uid:
        print("[ERROR] 未配置 WXPUSHER_APP_TOKEN 或 WXPUSHER_UID")
        sys.exit(1)

    print(f"\n  当前模式: {state['mode']}")
    print(f"  上次运行: {state.get('last_run', '首次运行')}")
    print(f"  监控源数量: {len(config['sources'])}")
    print(f"  关键词: {', '.join(config['keywords'])}")

    # 根据模式决定跑几轮
    if state["mode"] == "preheat":
        rounds = 3
        interval = 300  # 5分钟 = 300秒
    else:
        rounds = 1
        interval = 0

    for i in range(rounds):
        print(f"\n{'─' * 60}")
        print(f"  第 {i + 1}/{rounds} 轮检查")
        print(f"{'─' * 60}")

        run_one_round(config, state, app_token, uid)
        state["last_run"] = datetime.now().isoformat()
        save_state(state)

        # 不是最后一轮，等待
        if i < rounds - 1 and interval > 0:
            print(f"\n  ⏳ 等待 {interval // 60} 分钟后进行下一轮...")
            time.sleep(interval)

    print(f"\n{'=' * 60}")
    print(f"  本次监控完成，下次自动运行由 GitHub Actions 调度")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
