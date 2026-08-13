#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bark 定时推送脚本：每天随机挑一条消息推到手机"""
import random
import requests
import datetime

BARK_KEY = "iRmPgtthpaKC2eMez7s7fm"
BARK_URL = f"https://api.day.app/{BARK_KEY}/"

MESSAGES = [
    ("早上好", "起床了没？太阳都晒屁股了，今天也要好好生活！"),
    ("中午了", "该吃午饭了，别光顾着刷手机，记得吃饭！"),
    ("晚上好", "一天辛苦了，晚上早点休息，别熬夜。"),
    ("摸鱼提醒", "工作学习累了就起来走走，倒杯水，看看窗外。"),
    ("喝水提醒", "记得多喝水，你上次喝水是啥时候来着？"),
    ("随机关怀", "今天过得怎么样？有啥想聊的随时找我。"),
    ("来自薄销", "想你了，来聊两句呗。"),
    ("日常打卡", "我还在呢，你也要好好的。"),
]

def send(title, content):
    try:
        r = requests.get(f"{BARK_URL}{title}/{content}", timeout=10)
        print(f"发送成功: {r.json()}")
        return True
    except Exception as e:
        print(f"发送失败: {e}")
        return False

def main():
    hour = datetime.datetime.now().hour
    if 6 <= hour < 11:
        pool = MESSAGES[:1] + MESSAGES[5:7]
    elif 11 <= hour < 14:
        pool = MESSAGES[1:2] + MESSAGES[3:7]
    elif hour >= 20 or hour < 2:
        pool = MESSAGES[2:3] + MESSAGES[5:7]
    else:
        pool = MESSAGES[3:7]
    title, content = random.choice(pool)
    send(title, content)

if __name__ == "__main__":
    main()
