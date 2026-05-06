from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import time
import base64
import requests
import json
import re
import re
import urllib.parse

app = Flask(__name__)

# CORS
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
    "latvia": "🇱🇻"
}

LATVIA_KEY = "vless://c25c392a-3f5b-4cdc-bcd2-c2d566322a34@31.57.28.130:443?type=tcp&security=reality&encryption=none&flow=xtls-rprx-vision&sni=lv1.node.velum-vpn.ru&fp=randomized&pbk=b2CHaQlTFdnxLpNBjt5FKLH3jQabK6dvh8I30xZc5nM&sid=22e549172f59c481&spx=%2F"

_source_cache = {"ts": 0.0, "data": None}



def clean_name_from_key(key):
    try:
        name = key.split("#")[-1]
        name = urllib.parse.unquote(name)

        # удаляем [BL], [IPv6], [CIDR] и прочее
        name = re.sub(r"\[.*?\]", "", name)

        # убираем лишнее после |
        name = name.split("|")[0]

        return name.strip()
    except:
        return "🌍 Unknown"


# ===== CORE =====

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


# ===== CLEAN NAME =====

def clean_name(raw):
    if not raw:
        return ""

    raw = re.sub(r"\[.*?\]", "", raw)
    raw = raw.replace("_", " ")

    for sep in ["|", "-", "•", "/"]:
        raw = raw.split(sep)[0]

    return raw.strip()


# ===== SUB BUILD =====

def build_common(telegram_id=None):
    data = get_source_data()
    result = []

    # ===== CUSTOM LATVIA STABLE =====
    latvia_name = "⚡ | Латвия (стабильный сервер)"
    latvia_full = LATVIA_KEY + "#" + urllib.parse.quote(f"{FLAGS['latvia']} {latvia_name} @JadeVPNbot")
    result.append(("latvia", latvia_full, False, None))

    # ===== PRIORITY =====
    for c in PRIORITY:
        nodes = extract_all_variants(data, c)
        best = best_latency(nodes)
        if best:
            result.append((c, best, False, None))

    # ===== OTHER COUNTRIES (обычные) =====
    for c in data:
    	if c in ["updated_at", "other"] or c in PRIORITY or c.startswith("w_") or c == "russia":
            continue
        nodes = extract_all_variants(data, c)
        best = best_latency(nodes)
        if best:
            result.append((c, best, False, None))

    # ===== SPECIAL OTHER SECTION =====
    if "other" in data:
        for n in data["other"].get("top10", []):
            key = n.get("key")
            if key:
                result.append((c, best, False, None))

    # ===== OTHER COUNTRIES =====
    if "other_countries" in data:
        for country_name, info in data["other_countries"].items():
            nodes = info.get("top10", [])
            best = best_latency(nodes)

            if best:
                result.append((c, best, False, None))

    # ===== RUSSIA LTE =====
    nodes = extract_all_variants(data, "russia")
    best = best_latency(nodes)
    if best:
        result.append(("russia", best, True, None))

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
    out += "# traffic-limit: 0\n"
    out += "# Date/Time: " + date + "\n"

    if telegram_id:
        out += "# tg-id: " + str(telegram_id) + "\n"

    out += "# Количество: " + str(len(result)) + "\n\n"

    # ===== OUTPUT =====

    lte_counter = 1

    for item in result:
        if len(item) == 4:
            c, k, white, other_name = item
        else:
            c, k, white = item
            other_name = None

        flag = FLAGS.get(c, "🌍")

        if white:
            name = f"🚫 Обход #{lte_counter}"
            flag = FLAGS.get("russia", "")
            lte_counter += 1

        elif other_name:
            name = clean_name_from_key(k)

        elif c == "sweden":
            name = "⚡ | Швеция (стабильный сервер)"

        elif c == "germany":
            name = "⚡ | Германия (стабильный сервер)"

        else:
            name = RU.get(c, c)

        final_name = f"{flag} {name}".strip() + " @JadeVPNbot"

        out += clean(k, final_name) + "\n"

    return out


# ===== ROUTES =====

@app.route("/", methods=["GET"])
def home():
    return "JadeVPN running (Flask)"


@app.route("/sub/<telegram_id>", methods=["GET"])
@app.route("/subscriptions/<telegram_id>", methods=["GET"])
def get_sub(telegram_id):
    try:
        return Response(build_common(telegram_id), mimetype="text/plain")
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

        base_url = f"https://{request.headers.get('host')}"
        subscription_url = f"{base_url}/subscriptions/{telegram_id}"

        return jsonify({
            "id": telegram_id,
            "subscription_id": telegram_id,
            "key": subscription_url,
            "subscription_url": subscription_url
        })

    except Exception as e:
        return {"error": str(e)}, 500


# ===== DEEPLINK PAGE =====

@app.route("/deeplink/<telegram_id>", methods=["GET"])
def deeplink_page(telegram_id):
    try:
        base_url = f"https://{request.headers.get('host')}"
        subscription_url = f"{base_url}/subscriptions/{telegram_id}"
        deep_link = f"happ://add/{subscription_url}"

        html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>JadeVPN</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="background:#0f0f0f;color:white;font-family:Arial;text-align:center;padding-top:40px;">
<h2>🚀 Установка JadeVPN</h2>
<p>Нажмите кнопку ниже</p>
<button onclick="go()" style="padding:12px 20px;border-radius:10px;background:#2d6cdf;color:white;border:none;">Далее</button>
<script>
function go() {{
    setTimeout(() => {{
        window.location.href="{deep_link}";
    }},1000);
}}
</script>
</body>
</html>
"""
        return Response(html, mimetype="text/html")

    except Exception as e:
        return {"error": str(e)}, 500
