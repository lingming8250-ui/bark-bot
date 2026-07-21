from flask import Flask, request
import requests
import os

app = Flask(__name__)

BARK_KEY = "iRmPgtthpaKC2eMez7s7fm"
BARK_URL = f"https://api.day.app/{BARK_KEY}/"

@app.route("/")
def home():
    return "Bark Bot is running! 你的AI助手薄销已上线。"

@app.route("/send")
def send():
    msg = request.args.get("msg", "默认消息")
    title = request.args.get("title", "来自薄销的通知")
    
    try:
        r = requests.get(f"{BARK_URL}{title}/{msg}")
        return f"发送成功: {r.json()}"
    except Exception as e:
        return f"发送失败: {e}"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
