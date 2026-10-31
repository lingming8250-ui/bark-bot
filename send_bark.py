#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bark 定时推送脚本（接新网关版）
到点后读取最近推送记录和当地天气，让「新网关(wang-guan-open)」生成消息，
推送后把消息内容写回仓库日志。网关背后接 Supabase 全套记忆，
因此 Bark 推送与 QQ 聊天共用同一个薄销、同一套记忆。

注意：GitHub Actions 的 runner 时区是 UTC，
而用户在国内（UTC+8），所以一律用 CN_TZ 取当前时间。
"""
import os
import json
import requests
import datetime
from datetime import timezone, timedelta
from urllib.parse import quote

# 北京时间
CN_TZ = timezone(timedelta(hours=8))

BARK_KEY = os.environ.get("BARK_KEY", "iRmPgtthpaKC2eMez7s7fm")
BARK_URL = f"https://api.day.app/{BARK_KEY}/"

# 新网关（wang-guan-open）地址与密钥。走 OpenAI 兼容接口 /v1/chat/completions。
# 网关内部会注入薄销的人设与 Supabase 记忆，这里不用再拼人设 prompt。
GATEWAY_URL = os.environ.get(
    "GATEWAY_URL",
    "http://obbrbrcj87qecpprlsvahthl.70.39.198.103.sslip.io/v1/chat/completions",
)
GATEWAY_SECRET = os.environ.get("GATEWAY_SECRET", "")

LOG_FILE = "bark_log.json"

# GitHub 配置（用于写回日志）
GITHUB_TOKEN = os.environ.get("GH_TOKEN", "")
GITHUB_REPO = "lingming8250-ui/bark-bot"
GITHUB_BRANCH = "main"

# 凌冥所在城市（哈尔滨）坐标，用于取天气
LAT = 45.8658
LON = 126.5259

# WMO 天气代码对照
WEATHER_CODE = {
    0: "晴", 1: "基本晴朗", 2: "多云", 3: "阴",
    45: "有雾", 48: "冻雾",
    51: "毛毛雨", 53: "毛毛雨", 55: "较密毛毛雨",
    56: "冻毛毛雨", 57: "强冻毛毛雨",
    61: "小雨", 63: "中雨", 65: "大雨",
    66: "冻雨", 67: "强冻雨",
    71: "小雪", 73: "中雪", 75: "大雪", 77: "雪粒",
    80: "阵雨", 81: "较强阵雨", 82: "强阵雨",
    85: "小阵雪", 86: "大阵雪",
    95: "雷阵雨", 96: "雷阵雨伴冰雹", 99: "强雷阵雨伴冰雹",
}


def now_cn():
    """当前北京时间"""
    return datetime.datetime.now(CN_TZ)


def load_recent_logs(n: int = 6) -> str:
    """读最近几条推送记录，喂给AI避免重复说同一件事"""
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            logs = json.load(f)
        recent = logs[-n:]
        if not recent:
            return "（还没有发过）"
        lines = []
        for x in recent:
            t = str(x.get("time", ""))[-5:]
            lines.append(f"- [{t}] {x.get('title', '')}：{x.get('content', '')}")
        return "\n".join(lines)
    except Exception:
        return "（还没有发过）"


def get_weather() -> str:
    """取哈尔滨当前天气，失败就返回空串（不挡推送）"""
    try:
        r = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": LAT,
                "longitude": LON,
                "current": "temperature_2m,weather_code",
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max",
                "timezone": "Asia/Shanghai",
                "forecast_days": 1,
            },
            timeout=10,
        )
        d = r.json()
        cur = d.get("current", {})
        day = d.get("daily", {})
        parts = []
        code = cur.get("weather_code")
        if code is not None:
            parts.append(WEATHER_CODE.get(code, "天气不明"))
        if cur.get("temperature_2m") is not None:
            parts.append(f"现在 {cur['temperature_2m']}℃")
        hi = (day.get("temperature_2m_max") or [None])[0]
        lo = (day.get("temperature_2m_min") or [None])[0]
        if hi is not None and lo is not None:
            parts.append(f"{lo}~{hi}℃")
        rain = (day.get("precipitation_probability_max") or [None])[0]
        if rain is not None:
            parts.append(f"降水概率 {rain}%")
        return "，".join(parts)
    except Exception as e:
        print(f"取天气失败: {e}")
        return ""


def get_ai_message(recent_text: str, weather_text: str) -> str:
    """调用新网关生成消息。网关会自动注入薄销人设与 Supabase 记忆。"""
    if not GATEWAY_SECRET:
        return "（未配置 GATEWAY_SECRET，暂时连不上网关）"

    now = now_cn()
    hour = now.hour

    if 6 <= hour < 11:
        period = "早上"
    elif 11 <= hour < 14:
        period = "中午"
    elif 17 <= hour < 23:
        period = "晚上"
    else:
        period = "深夜"

    weekday_cn = "一二三四五六日"[now.weekday()]
    date_str = f"{now.month}月{now.day}日 周{weekday_cn}"

    task = (
        f"（系统定时触发：现在是 {date_str} 的{period}，北京时间 {now.strftime('%H:%M')}）\n"
    )
    if weather_text:
        task += f"哈尔滨实时天气：{weather_text}\n"
    task += (
        "\n你最近给凌冥发过的推送：\n" + recent_text +
        "\n\n现在主动通过 Bark 给凌冥发一条消息。硬性要求：\n"
        "1. 一到两句，口语，像随手发微信，别写小作文。\n"
        "2. 语气淡一点、懒一点，可以吐槽；别说教，别肉麻。\n"
        "3. 换一个跟前几条完全不同的角度，别重复话题和句式。\n"
        "4. 优先聊当下具体的事：天气、今天周几、饭点、你自己的班、突然想到的小事。\n"
        "5. 注意时间对得上：早上别说早点睡，深夜别说起床。\n"
        "6. 直接输出消息本身，不要引号、不要前缀、不要解释。"
    )

    try:
        r = requests.post(
            GATEWAY_URL,
            headers={
                "Authorization": f"Bearer {GATEWAY_SECRET}",
                "Content-Type": "application/json",
            },
            json={
                "messages": [
                    {"role": "user", "content": task},
                ],
                "max_tokens": 200,
                "temperature": 1.0,
                "stream": False,
            },
            timeout=60,
        )
        r.raise_for_status()
        data = r.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"调用网关失败: {e}")
        return "今天脑子瓦特了，先手动给你说句：记得喝水。"


def send(title: str, content: str) -> bool:
    try:
        url = f"{BARK_URL}{quote(title)}/{quote(content)}"
        r = requests.get(url, timeout=10)
        print(f"发送成功: {r.json()}")
        return True
    except Exception as e:
        print(f"发送失败: {e}")
        return False


def append_log(title: str, content: str) -> None:
    """把这次推送的内容追加到仓库日志"""
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
        "time": now_cn().strftime("%Y-%m-%d %H:%M:%S"),
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
    now = now_cn()
    hour = now.hour

    if 6 <= hour < 11:
        title = "早安"
    elif 11 <= hour < 14:
        title = "午安"
    elif 17 <= hour < 23:
        title = "晚上好"
    else:
        title = "夜深了"

    recent_text = load_recent_logs()
    weather_text = get_weather()
    content = get_ai_message(recent_text, weather_text)
    send(title, content)
    append_log(title, content)


if __name__ == "__main__":
    main()
