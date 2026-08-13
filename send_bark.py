#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bark 定时推送脚本（共享记忆版）
到点后读取记忆库，让 DeepSeek 基于记忆生成一条生动的消息
"""
import os
import json
import requests
import datetime

BARK_KEY = "iRmPgtthpaKC2eMez7s7fm"
BARK_URL = f"https://api.day.app/{BARK_KEY}/"
DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"
MEMORY_FILE = "memory.json"


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


if __name__ == "__main__":
    main()
