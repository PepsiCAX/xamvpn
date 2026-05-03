from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import time
import base64
import requests
import json

app = Flask(__name__)

# ✅ CORS включён
CORS(app, resources={r"/*": {"origins": "*"}})

SOURCE = "https://tiagorrg.github.io/vless-checker/keys.json"
SOURCE_CACHE_TTL_SEC = 300

PRIORITY = ["netherlands", "germany", "baltics"]

RU = {
    "netherlands": "Нидерланды",
    "germany": "Германия",
    "baltics": "Прибалтика",
    "finland": "Финляндия",
    "russia": "Россия",
    "poland": "Польша",
    "sweden": "Швеция"
}

FLAGS = {
    "netherlands": "🇳🇱",
    "germany": "🇩🇪",
    "baltics": "🇪🇪",
    "finland": "🇫🇮",
    "russia": "🇷🇺",
    "poland": "🇵🇱",
    "sweden": "🇸🇪"
}

_source_cache = {"ts": 0.0, "data": None}

# ===== CORE LOGIC =====

def get_source_data():
    now = time.time()
    if _source_cache["data"] and (now - _source_cache["ts"]) < SOURCE_CACHE_TTL_SEC:
        return _source_cache["data"]
    data = requests.get(SOURCE, timeout=10).json()
    _source_cache["ts"] = now
    _source_cache["data"] = data
    return data


def best_latency(nodes):
    if not nodes:
        return None
    best = None
    best_ping = 999999
    for n in nodes:
        key = n.get("key")
        ping = n.get("latency_ms", 999999)
        if key and ping < best_ping:
            best = key
            best_ping = ping
    return best


def extract_all_variants(data, country):
    nodes = []
    if country in data:
        nodes += data[country].get("top10", [])
    w_key = "w_" + country
    if w_key in data:
        nodes += data[w_key].get("top10", [])
    return nodes


def clean(key, name):
    return key.split("#")[0] + "#" + name


def build_common(telegram_id=None):
    data = get_source_data()
    result = []

    for c in PRIORITY:
        nodes = extract_all_variants(data, c)
        best = best_latency(nodes)
        if best:
            result.append((c, best, False))

    for c in data:
        if c in ["updated_at"] or c in PRIORITY or c.startswith("w_"):
            continue
        nodes = extract_all_variants(data, c)
        best = best_latency(nodes)
        if best:
            result.append((c, best, False))

    nodes = extract_all_variants(data, "russia")
    best = best_latency(nodes)
    if best:
        result.append(("russia", best, True))

    announce_text = (
    "JadeVPN 🚀\n"
    "⚡ — стабильные серверы\n"
    "LTE — обход белых списков\n"
    "Подключение автоматически оптимизируется под сеть"
    )

    if telegram_id:
        announce_text += f"\nID: {telegram_id}"

    announce = base64.b64encode(announce_text.encode()).decode()
    expire = int(time.time()) + 30 * 24 * 60 * 60
    date = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())

    out = ""
    out += "# profile-title: 🟩 JadeVPN 🟩\n"
    out += "# profile-update-interval: 5\n"
    out += "# support-url: https://t.me/JadeVPN_ru\n"
    out += "# profile-web-page-url: https://jadevpn.local\n"
    out += "# announce: base64:" + announce + "\n"
    out += f"# subscription-userinfo: upload=0; download=0; total=0; expire={expire}\n"
    out += "# traffic-limit: 0\n"
    out += "# Date/Time: " + date + "\n"

    if telegram_id:
        out += "# tg-id: " + str(telegram_id) + "\n"

    out += "# Количество: " + str(len(result)) + "\n\n"

    for c, k, white in result:
        if white:
            name = "LTE | Белые списки"
            flag = FLAGS.get("russia", "")
        elif c == "sweden":
            name = "⚡ | Швеция (стабильный сервер)"
            flag = FLAGS.get(c, "")
        else:
            name = RU.get(c, c)
            flag = FLAGS.get(c, "")

    return out


# ===== ROUTES =====

@app.route("/", methods=["GET"])
def home():
    return "JadeVPN running (Flask on Vercel)"


@app.route("/sub/<telegram_id>", methods=["GET"])
@app.route("/subscriptions/<telegram_id>", methods=["GET"])
def get_sub(telegram_id):
    try:
        content = build_common(telegram_id)
        return Response(content, mimetype="text/plain")
    except Exception as e:
        return str(e), 500


@app.route("/sub", methods=["POST"])
@app.route("/subscriptions", methods=["POST"])
def create_sub():
    try:
        body = request.get_json(force=True) or {}

        telegram_id = str(
            body.get("telegram_id")
            or body.get("telegramId")
            or body.get("id")
            or "0"
        )

        base_url = request.headers.get("x-forwarded-proto", "https") + "://" + request.headers.get("host", "")
        subscription_url = f"{base_url}/subscriptions/{telegram_id}"

        return jsonify({
            "id": telegram_id,
            "subscription_id": telegram_id,
            "key": subscription_url,
            "subscription_url": subscription_url,
            "key_list_url": subscription_url
        })

    except Exception as e:
        return {"error": str(e)}, 500
        

@app.route("/deeplink/<telegram_id>", methods=["GET"])
def deeplink_page(telegram_id):
    try:
        base_url = f"https://{request.headers.get('host')}"
        subscription_url = f"{base_url}/subscriptions/{telegram_id}"
        deep_link = f"happ://add/{subscription_url}"

        html = f"""
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="utf-8">
    <title>JadeVPN Setup</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">

    <style>
        body {{
            margin: 0;
            font-family: Arial, sans-serif;
            background: #0f0f0f;
            color: white;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
        }}

        .card {{
            width: 90%;
            max-width: 420px;
            background: #1c1c1c;
            padding: 20px;
            border-radius: 14px;
            text-align: center;
        }}

        a, button {{
            display: block;
            margin: 10px auto;
            padding: 12px;
            border-radius: 10px;
            text-decoration: none;
            border: none;
            cursor: pointer;
            width: 90%;
            font-size: 15px;
        }}

        .store {{
            background: #2c2c2c;
            color: white;
        }}

        .btn {{
            background: #2d6cdf;
            color: white;
        }}

        #msg {{
            display: none;
            margin-top: 15px;
            color: #4ade80;
        }}
    </style>
</head>

<body>

<div class="card">
    <h2>🚀 Установка JadeVPN</h2>

    <p>1. Установите приложение Happ VPN</p>

    <a id="ios" class="store" href="https://apps.apple.com" style="display:none;">📱 App Store</a>
    <a id="android" class="store" href="https://play.google.com" style="display:none;">🤖 Google Play</a>

    <p>2. После установки нажмите “Далее”</p>

    <button class="btn" onclick="go()">Далее</button>

    <div id="msg">Спасибо за выбор JadeVPN ❤️</div>
</div>

<script>
function detectOS() {{
    const ua = navigator.userAgent.toLowerCase();

    if (ua.includes("android")) {{
        document.getElementById("android").style.display = "block";
    }} else if (ua.includes("iphone") || ua.includes("ipad")) {{
        document.getElementById("ios").style.display = "block";
    }} else {{
        document.getElementById("ios").style.display = "block";
        document.getElementById("android").style.display = "block";
    }}
}}

function go() {{
    document.getElementById("msg").style.display = "block";

    setTimeout(() => {{
        window.location.href = "{deep_link}";
    }}, 1200);
}}

window.onload = detectOS;
</script>

</body>
</html>
"""

        return Response(html, mimetype="text/html")

    except Exception as e:
        return {"error": str(e)}, 500
