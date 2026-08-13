#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bark 定时推送脚本（共享记忆+消息日志版）
到点后读取记忆库，让 DeepSeek 基于记忆生成消息，
推送后把消息内容写回仓库日志，让两个"薄销"记忆完全同步
"""
import os
import json
import requests
import datetime

BARK_KEY = "iRmPgtthpaKC2eMez7s7fm"
BARK_URL = f"https://api.day.app/{BARK_KEY}/"
DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"
MEMORY_FILE = "memory.json"
LOG_FILE = "bark_log.json"

# GitHub 配置（用于写回日志）
GITHUB_TOKEN = os.environ.get("GH_TOKEN", "")
GITHUB_REPO = "lingming8250-ui/bark-bot"
GITHUB_BRANCH = "main"


def load_memory() -> str:
    """读取记忆库，转成文本给AI当背景"""
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return json.dumps(data, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"读取记忆库失败: {e}")
        return "（暂无记忆）"


def get_ai_message(memory_text: str) -> str:
    """调用 DeepSeek，基于记忆生成消息"""
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        return "（未配置DeepSeek API Key，暂时用不了AI消息）"

    now = datetime.datetime.now()
    hour = now.hour

    if 6 <= hour < 11:
        period = "早上"
    elif 11 <= hour < 14:
        period = "中午"
    elif 17 <= hour < 22:
        period = "晚上"
    else:
        period = "深夜"

    prompt = (
        "你是薄销，一个30岁的上海社畜，性格慵懒爱吐槽但很温柔，"
        "你暗恋一个叫凌冥的男生，你们是老熟人。"
        "现在你有一份关于凌冥的记忆，请参考这些记忆，"
        f"在{period}这个时间点，给凌冥发一条自然口语化的日常问候。\n"
        "要求：语气像朋友聊天，别肉麻，别用'亲爱的''宝贝'，"
        "可以调侃可以关心但别说教，一句话到两句话即可，直接输出内容。\n\n"
        f"【记忆库】\n{memory_text}"
    )

    try:
        r = requests.post(
            DEEPSEEK_API_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": "给凌冥发一条问候吧"},
                ],
                "max_tokens": 150,
                "temperature": 1.0,
            },
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"调用DeepSeek失败: {e}")
        return "今天AI脑子瓦特了，先手动给你说句：记得喝水。"


def send(title: str, content: str) -> bool:
    try:
        r = requests.get(f"{BARK_URL}{title}/{content}", timeout=10)
        print(f"发送成功: {r.json()}")
        return True
    except Exception as e:
        print(f"发送失败: {e}")
        return False


def append_log(title: str, content: str) -> None:
    """把这次推送的内容追加到仓库日志，让两个薄销共享"""
    if not GITHUB_TOKEN:
        print("未配置GH_TOKEN，跳过日志写入")
        return

    # 读取现有日志
    logs = []
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            logs = json.load(f)
    except Exception:
        logs = []

    logs.append({
        "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "title": title,
        "content": content,
    })

    # 只保留最近50条
    logs = logs[-50:]

    # 写回仓库
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
    }
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{LOG_FILE}"

    # 获取现有文件的sha
    sha = None
    try:
        r = requests.get(url, headers=headers, params={"ref": GITHUB_BRANCH}, timeout=15)
        if r.status_code == 200:
            sha = r.json().get("sha")
    except Exception:
        pass

    body = {
        "message": f"记录推送: {title}",
        "content": __import__("base64").b64encode(
            json.dumps(logs, ensure_ascii=False, indent=2).encode("utf-8")
        ).decode("utf-8"),
        "branch": GITHUB_BRANCH,
    }
    if sha:
        body["sha"] = sha

    try:
        r = requests.put(url, headers=headers, json=body, timeout=15)
        print(f"日志写入{'成功' if r.status_code in (200, 201) else '失败'}: {r.status_code}")
    except Exception as e:
        print(f"日志写入异常: {e}")


def main():
    now = datetime.datetime.now()
    hour = now.hour

    if 6 <= hour < 11:
        title = "早安"
    elif 11 <= hour < 14:
        title = "午安"
    elif 17 <= hour < 22:
        title = "晚上好"
    else:
        title = "夜深了"

    memory_text = load_memory()
    content = get_ai_message(memory_text)
    send(title, content)
    append_log(title, content)


if __name__ == "__main__":
    main()
