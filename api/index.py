from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import time
import base64
import requests
import re
import urllib.parse

app = Flask(__name__)

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
    "sweden": "Швеция",
    "latvia": "Латвия"
}

FLAGS = {
    "netherlands": "🇳🇱",
    "germany": "🇩🇪",
    "baltics": "🇪🇪",
    "finland": "🇫🇮",
    "russia": "🇷🇺",
    "poland": "🇵🇱",
    "sweden": "🇸🇪",
    "germany_speed": "🇩🇪",
    "latvia": "🇱🇻",
    "bypass": "🚫"
}

# 🔥 стабильные сервера JadeVPN

LATVIA_KEY = "vless://d3906aaf-5b41-4af1-a9b2-b0df37ef6a62@lt-1.nodes.ac:443?encryption=none&flow=xtls-rprx-vision&security=reality&sni=lt-1.nodes.ac&fp=chrome&pbk=U-9TbiZdFk2cJDz87uISYD4EcbChAxlgckirdj6uwnI&sid=9744dc64c70b7c96&type=tcp"

GERMANY_MAX_SPPED_KEY = "vless://1781a225-945c-49c3-85a5-2f6c7e425b2f@5.178.101.109:8447?encryption=none&security=reality&flow=xtls-rprx-vision&sni=www.volkswagen.de&fp=chrome&pbk=kBTMVLCNE0jjwuJF6H5-65l5Pe0QToS0Hg-9Tmaa7Sk&sid=1a2b3c4d&type=tcp&spx=%2F"



GERMANY_SPEED_KEY = "vless://d3906aaf-5b41-4af1-a9b2-b0df37ef6a62@deu-1.nodes.ac:443?encryption=none&flow=xtls-rprx-vision&security=reality&sni=deu-1.nodes.ac&fp=chrome&pbk=17oT99vO8kHKvbL1Qu0HJ5J5vAhC1Jp1NBdQrdSZjSw&sid=193409f66d2d9844&type=tcp"

LTE_BYPASS_KEY = "vless://d3906aaf-5b41-4af1-a9b2-b0df37ef6a62@wl-1-1.legendary.ac:443?encryption=none&flow=xtls-rprx-vision&security=reality&sni=wl-1-1.legendary.ac&fp=chrome&pbk=Ce2abow3fU3pN2_mlX3uJW93sBMgTI9qNo5q7_EgFTA&sid=c4a70eddb745b1ea&type=tcp"

_source_cache = {"ts": 0.0, "data": None}


def clean_name_from_key(key):
    try:
        name = key.split("#")[-1]
        name = urllib.parse.unquote(name)
        name = re.sub(r"\[.*?\]", "", name)
        name = name.split("|")[0]
        return name.strip()
    except:
        return "🌍 Unknown"


def get_source_data():
    now = time.time()
    if _source_cache["data"] and (now - _source_cache["ts"]) < SOURCE_CACHE_TTL_SEC:
        return _source_cache["data"]
    data = requests.get(SOURCE, timeout=10).json()
    _source_cache["ts"] = now
    _source_cache["data"] = data
    return data


def best_latency(nodes):
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


# ===== SUB BUILD =====

def build_common(telegram_id=None):
    data = get_source_data()
    result = []

    # ===== 🇱🇻 LATVIA (ВСЕГДА ПЕРВАЯ) =====
    latvia_name = "⚡ | Латвия (стабильный сервер)"
    latvia_full = LATVIA_KEY + "#" + urllib.parse.quote(f"{FLAGS['latvia']} {latvia_name} @JadeVPNbot")
    result.append(("latvia", latvia_full, False, None))

    # ===== 🇩🇪 GERMANY SPEED =====
    germany_speed_name = "⚡ | Германия (скоростной сервер)"
    germany_speed_full = GERMANY_SPEED_KEY + "#" + urllib.parse.quote(
        f"🇩🇪 {germany_speed_name} @JadeVPNbot"
    )
    result.append(("germany_speed", germany_speed_full, False, None))

    # ===== 🚫 WHITE LIST BYPASS =====
    GERMANY_MAX_SPEED_NAME = "🇩🇪 Германия #3 ⚡10 Gbit"
    germanygbps_full = GERMANY_MAX_SPPED_KEY + "#" + urllib.parse.quote(
        f"{FLAGS['germany']} {GERMANY_MAX_SPEED_NAME} @JadeVPNbot"
    )
    result.append(("gbpsgermany", germanygbps_full, False, None))

    # ===== 🚫 WHITE LIST BYPASS =====
    bypass_name = "Обход #2"
    bypass_full = LTE_BYPASS_KEY + "#" + urllib.parse.quote(
        f"{bypass_name} @JadeVPNbot"
    )
    result.append(("bypass", bypass_full, False, None))
    
    # ===== PRIORITY =====
    for c in PRIORITY:
        nodes = extract_all_variants(data, c)
        best = best_latency(nodes)
        if best:
            result.append((c, best, False, None))

    # ===== OTHER COUNTRIES =====
    for c in data:
        if c in ["updated_at", "other"] or c in PRIORITY or c.startswith("w_") or c == "russia":
            continue
        nodes = extract_all_variants(data, c)
        best = best_latency(nodes)
        if best:
            result.append((c, best, False, None))

    # ===== OTHER (РАЗНЫЕ СТРАНЫ) =====
    if "other" in data:
        for n in data["other"].get("top10", []):
            key = n.get("key")
            if key:
                name = clean_name_from_key(key)
                result.append(("other", key, False, name))

    # ===== OTHER COUNTRIES (РАСШИРЕННЫЕ) =====
    if "other_countries" in data:
        for country_name, info in data["other_countries"].items():
            nodes = info.get("top10", [])
            best = best_latency(nodes)
            if best:
                result.append((country_name.lower(), best, False, country_name))

    # ===== 🇷🇺 RUSSIA LTE (ТОЛЬКО 1) =====
    nodes = extract_all_variants(data, "russia")[:2]
    best = best_latency(nodes)
    if best:
        result.append(("russia", best, True, None))

    # ===== REMOVE DUPLICATES =====
    unique = []
    seen = set()

    for item in result:
        key = item[1]
        if key not in seen:
            seen.add(key)
            unique.append(item)

    result = unique

    # ===== META =====
    announce_text = "JadeVPN 🚀 | ⚡ стабильные | LTE обход | авто-оптимизация"
    if telegram_id:
        announce_text += f" | ID:{telegram_id}"

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
    out += "# Date/Time: " + date + "\n"

    if telegram_id:
        out += "# tg-id: " + str(telegram_id) + "\n"

    out += "# Количество: " + str(len(result)) + "\n\n"

    # ===== OUTPUT =====
    lte_counter = 1

    for c, k, white, other_name in result:
        flag = FLAGS.get(c, "🌍")

        if white:
            name = f"🚫 Обход #{lte_counter}"
            flag = FLAGS.get("russia", "")
            lte_counter += 1

        elif other_name:
            name = other_name

        elif c == "sweden":
            name = "⚡ | Швеция (стабильный сервер)"

        elif c == "germany":
            name = "⚡ | Германия"

        elif c == "germany_speed":
            name = "⚡ | Германия (скоростной сервер)"

        elif c == "bypass":
            name = "🚫 Обход #2"

        elif c == "gbpsgermany":
            name = "Германия #3 ⚡10 Gbit"

        else:
            name = RU.get(c, c)

        final_name = f"{flag} {name}".strip() + " @JadeVPNbot"
        out += clean(k, final_name) + "\n"

    return out


# ===== ROUTES =====

@app.route("/", methods=["GET"])
def home():
    return "JadeVPN running"


@app.route("/subscriptions/<telegram_id>", methods=["GET"])
def get_sub(telegram_id):
    return Response(build_common(telegram_id), mimetype="text/plain")


@app.route("/subscriptions", methods=["POST"])
def create_sub():
    body = request.get_json(force=True) or {}
    telegram_id = str(body.get("telegram_id", "0"))

    base_url = f"https://{request.headers.get('host')}"
    subscription_url = f"{base_url}/subscriptions/{telegram_id}"

    return jsonify({
        "id": telegram_id,
        "subscription_url": subscription_url
    })


@app.route("/deeplink/<telegram_id>", methods=["GET"])
def deeplink_page(telegram_id):
    try:
        base_url = f"https://{request.headers.get('host')}"
        subscription_url = f"{base_url}/subscriptions/{telegram_id}"

        happ_link = f"happ://add/{subscription_url}"

        html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>JadeVPN</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<style>
body {{
    background:#0f0f0f;
    color:white;
    font-family:Arial;
    text-align:center;
    padding:30px;
}}

.btn {{
    display:block;
    margin:10px auto;
    padding:14px;
    width:280px;
    border-radius:14px;
    background:#2d6cdf;
    color:white;
    text-decoration:none;
    font-size:16px;
}}

.store {{
    background:#1c1c1c;
}}

</style>
</head>
<body>

<h1>🚀 JadeVPN</h1>
<p>Подключение через Happ</p>

<a class="btn" onclick="connect()">⚡ Открыть в Happ</a>

<h3>📥 Скачать Happ</h3>

<a class="btn store" href="https://apps.apple.com/">🍎 App Store (iOS)</a>
<a class="btn store" href="https://play.google.com/store">🤖 Google Play (Android)</a>
<a class="btn store" href="https://www.microsoft.com/store">💻 Microsoft Store (Windows)</a>
<a class="btn store" href="https://snapcraft.io/">🐧 Linux (Snap / Flatpak)</a>

<script>
function connect() {{
    window.location.href = "{happ_link}";

    setTimeout(() => {{
        window.location.href = "{subscription_url}";
    }}, 1500);
}}
</script>

</body>
</html>
"""
        return Response(html, mimetype="text/html")

    except Exception as e:
        return {{"error": str(e)}}, 500
