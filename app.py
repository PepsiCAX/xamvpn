import time
import base64
import requests
import json

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

# ===== CORE LOGIC (НЕ ТРОГАЛ) =====

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
        f"Добро пожаловать в JadeVPN, ID: {telegram_id} 🚀"
        if telegram_id else
        "Добро пожаловать в JadeVPN 🚀"
    )

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
        else:
            name = RU.get(c, c)
            flag = FLAGS.get(c, "")
        final_name = f"{flag} {name}".strip()
        out += clean(k, final_name) + "\n"

    return out

# ===== VERCEL HANDLER =====

def handler(request):
    path = request.path
    method = request.method

    # ---- GET ----
    if method == "GET":

        if path.startswith("/sub") or path.startswith("/subscriptions"):
            parts = path.split("/")
            telegram_id = parts[2] if len(parts) > 2 and parts[2] else "0"

            try:
                content = build_common(telegram_id)
                return {
                    "statusCode": 200,
                    "headers": {
                        "Content-Type": "text/plain; charset=utf-8",
                        "Access-Control-Allow-Origin": "*"
                    },
                    "body": content
                }
            except Exception as e:
                return {"statusCode": 500, "body": str(e)}

        return {
            "statusCode": 200,
            "body": "JadeVPN running (Vercel)"
        }

    # ---- POST ----
    if method == "POST":
        if path.startswith("/sub") or path.startswith("/subscriptions"):
            try:
                body = request.get_json() or {}
                telegram_id = str(
                    body.get("telegram_id")
                    or body.get("telegramId")
                    or body.get("id")
                    or "0"
                )

                base_url = request.headers.get("x-forwarded-proto", "https") + "://" + request.headers.get("host")

                subscription_url = f"{base_url}/subscriptions/{telegram_id}"

                return {
                    "statusCode": 200,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({
                        "id": telegram_id,
                        "subscription_id": telegram_id,
                        "key": subscription_url,
                        "subscription_url": subscription_url,
                        "key_list_url": subscription_url
                    })
                }

            except Exception as e:
                return {"statusCode": 500, "body": str(e)}

    return {"statusCode": 404, "body": "Not found"}
