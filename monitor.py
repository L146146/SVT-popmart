#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SEVENTEEN × 泡泡玛特 发售信息监控脚本
功能：定时抓取目标页面，检测关键词新增命中，通过 wxpusher 推送微信通知
"""

import requests
import json
import time
import os
import sys
from datetime import datetime

# ============ 配置 ============
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
STATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state.json")
WXPUSHER_URL = "https://wxpusher.zjiecode.com/api/up/send-message"

# 请求头，模拟手机浏览器（移动端页面更好抓）
HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                  "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 "
                  "Mobile/15E148 Safari/604.1",
    "Accept-Language": "zh-CN,zh;q=0.9",
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


def send_wxpusher(app_token, uids, title, content, url=None):
    """通过 wxpusher 推送消息到微信"""
    payload = {
        "appToken": app_token,
        "content": content,
        "summary": title[:100],
        "contentType": 3,
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
    sources = config["sources"]
    uids = [uid]
    new_alerts = []

    for source in sources:
        name = source["name"]
        url = source["url"]
        keywords = source["keywords"]
        alert_on_first = source.get("alert_on_first_hit", True)

        print(f"\n  [CHECK] {name}")
        print(f"          {url}")

        content = fetch_page(url)
        if not content:
            continue

        current_hits = check_keywords(content, keywords)

        prev = state["last_results"].get(name, {})
        prev_hits = prev.get("hits", [])
        is_first = name not in state["last_results"]

        # 找出新增的关键词（这次命中了，但上次没命中）
        new_keywords = [kw for kw in current_hits if kw not in prev_hits]

        # 判断是否需要推送
        should_alert = False
        alert_reason = ""

        if is_first and not alert_on_first:
            # 首次运行且不提醒首次命中 → 只记录不推送
            print(f"  - 首次记录基准，命中: {current_hits if current_hits else '无'}（不推送）")
        elif new_keywords:
            # 有新增命中的关键词 → 推送
            should_alert = True
            alert_reason = f"新增命中: {', '.join(new_keywords)}"
            print(f"  🎯 {alert_reason}")
        elif current_hits:
            print(f"  ✓ 已命中，无新增关键词（跳过）")
        else:
            print(f"  - 未命中关键词")

        if should_alert:
            new_alerts.append({
                "source": name,
                "url": url,
                "new_keywords": new_keywords,
                "all_hits": current_hits,
            })

        # 更新状态
        state["last_results"][name] = {
            "hits": current_hits,
            "checked_at": datetime.now().isoformat(),
        }

    # 有新警报 → 推送
    if new_alerts:
        title = "🔔 SEVENTEEN × 泡泡玛特 监控警报！"
        parts = []
        for i, alert in enumerate(new_alerts, 1):
            parts.append(f"### {i}. {alert['source']}")
            parts.append(f"**新增触发**: {', '.join(alert['new_keywords'])}")
            parts.append(f"**当前命中**: {', '.join(alert['all_hits'])}")
            parts.append(f"**链接**: {alert['url']}")
            parts.append("")

        content = "\n".join(parts)
        push_url = new_alerts[0]["url"]

        send_wxpusher(app_token, uids, title, content, push_url)

        # 首次命中 → 切换到预热模式
        if state["mode"] == "normal":
            state["mode"] = "preheat"
            print(f"\n  ⚡ 进入预热模式（后续频率加密）")

    return new_alerts


def main():
    print("=" * 60)
    print(f"  SEVENTEEN × 泡泡玛特 监控启动")
    print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    config = load_config()
    state = load_state()

    app_token = os.environ.get("WXPUSHER_APP_TOKEN", "").strip()
    uid = os.environ.get("WXPUSHER_UID", "").strip()

    if not app_token or not uid:
        print("[ERROR] 未配置 WXPUSHER_APP_TOKEN 或 WXPUSHER_UID")
        sys.exit(1)

    print(f"\n  当前模式: {state['mode']}")
    print(f"  上次运行: {state.get('last_run', '首次运行')}")
    print(f"  监控源数量: {len(config['sources'])}")

    for s in config["sources"]:
        print(f"    - {s['name']}: {len(s['keywords'])} 个关键词")

    # 根据模式决定跑几轮
    if state["mode"] == "preheat":
        rounds = 3
        interval = 300  # 5分钟
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

        if i < rounds - 1 and interval > 0:
            print(f"\n  ⏳ 等待 {interval // 60} 分钟后进行下一轮...")
            time.sleep(interval)

    print(f"\n{'=' * 60}")
    print(f"  本次监控完成")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
