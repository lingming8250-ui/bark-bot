#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bark 定时推送脚本（AI版）
到点后调用 DeepSeek 生成一条生动的消息，推送到手机
"""
import os
import random
import requests
import datetime

BARK_KEY = "iRmPgtthpaKC2eMez7s7fm"
BARK_URL = f"https://api.day.app/{BARK_KEY}/"
DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"


def get_ai_message() -> str:
    """调用 DeepSeek 生成一条消息"""
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

    # 给DeepSeek的人设和任务
    prompt = (
        "你是一个名叫薄销的30岁社畜，性格慵懒爱吐槽但很温柔，"
        "你在给一个叫凌冥的男生发一条日常问候。"
        f"现在是{period}，请用一句话，语气自然、口语化、像朋友之间聊天，"
        "不要用'亲爱的''宝贝'这类肉麻称呼，不要用感叹号堆砌，"
        "可以带点调侃或关心，但别太说教。直接输出内容，不要加引号。"
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
                "max_tokens": 100,
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

    # 按时段决定标题
    if 6 <= hour < 11:
        title = "早安"
    elif 11 <= hour < 14:
        title = "午安"
    elif 17 <= hour < 22:
        title = "晚上好"
    else:
        title = "夜深了"

    content = get_ai_message()
    send(title, content)


if __name__ == "__main__":
    main()
