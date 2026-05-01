from http.server import BaseHTTPRequestHandler, HTTPServer
import time
import base64
import requests
import json

SOURCE = "https://tiagorrg.github.io/vless-checker/keys.json"
DATA_FILE = "subscriptions.json"
SOURCE_CACHE_TTL_SEC = 300

subscriptions = {}

try:
    with open(DATA_FILE, "r") as f:
        subscriptions = json.load(f)
except:
    subscriptions = {}

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

def get_source_data():
    now = time.time()
    if _source_cache["data"] is not None and (now - _source_cache["ts"]) < SOURCE_CACHE_TTL_SEC:
        return _source_cache["data"]
    data = requests.get(SOURCE, timeout=10).json()
    _source_cache["ts"] = now
    _source_cache["data"] = data
    return data

def best_latency(nodes):
    """выбираем сервер с минимальной latency"""
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
    """собираем country + w_country"""
    nodes = []
    if country in data:
        for s in data[country].get("top10", []):
            nodes.append(s)
    w_key = "w_" + country
    if w_key in data:
        for s in data[w_key].get("top10", []):
            nodes.append(s)
    return nodes

def clean(key, name):
    return key.split("#")[0] + "#" + name

def build():
    data = get_source_data()
    result = []
    # приоритет стран
    for c in PRIORITY:
        nodes = extract_all_variants(data, c)
        best = best_latency(nodes)
        if best:
            result.append((c, best, False))
    # остальные
    for c in data:
        if c in ["updated_at"] or c in PRIORITY or c.startswith("w_"):
            continue
        nodes = extract_all_variants(data, c)
        best = best_latency(nodes)
        if best:
            result.append((c, best, False))
    # white list (Russia)
    nodes = extract_all_variants(data, "russia")
    best = best_latency(nodes)
    if best:
        result.append(("russia", best, True))
    # ===== HEADER =====
    announce = base64.b64encode("Добро пожаловать в JadeVPN 🚀".encode()).decode()
    expire = int(time.time()) + 30 * 24 * 60 * 60
    date = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
    out = ""
    out += "# profile-title: 🟩 JadeVPN 🟩\n"
    out += "# profile-update-interval: 5\n"
    out += "# support-url: https://t.me/JadeVPN_ru\n"
    out += "# profile-web-page-url: https://jadevpn.local\n"
    out += "# announce: base64:" + announce + "\n"
    out += "# subscription-userinfo: upload=0; download=0; total=0; expire=" + str(expire) + "\n"
    out += "# traffic-limit: 0\n"
    out += "# Date/Time: " + date + "\n"
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

def build_for_user(telegram_id):
    """генерирует подписку для конкретного пользователя"""
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
    announce = base64.b64encode(f"Добро пожаловать в JadeVPN, ID: {telegram_id} 🚀".encode()).decode()
    expire = int(time.time()) + 30 * 24 * 60 * 60
    date = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
    out = ""
    out += "# profile-title: 🟩 JadeVPN 🟩\n"
    out += "# profile-update-interval: 5\n"
    out += "# support-url: https://t.me/JadeVPN_ru\n"
    out += "# profile-web-page-url: https://jadevpn.local\n"
    out += "# announce: base64:" + announce + "\n"
    out += "# subscription-userinfo: upload=0; download=0; total=0; expire=" + str(expire) + "\n"
    out += "# traffic-limit: 0\n"
    out += "# Date/Time: " + date + "\n"
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

class Handler(BaseHTTPRequestHandler):
    def _base_url(self):
        # Respect reverse proxies if the mini app is behind one.
        proto = self.headers.get("X-Forwarded-Proto") or "http"
        host = self.headers.get("Host") or "localhost:8000"
        return f"{proto}://{host}"

    def _send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
    
    def do_OPTIONS(self):
        self.send_response(200)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self):
        if self.path.startswith("/sub"):
            parts = self.path.split("/")
            if len(parts) >= 3 and parts[2]:
                telegram_id = parts[2]
            else:
                telegram_id = "0"
            try:
                content = build_for_user(telegram_id)
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(content.encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(str(e).encode())
        elif self.path.startswith("/subscriptions/"):
            parts = self.path.split("/")
            if len(parts) >= 3 and parts[2]:
                telegram_id = parts[2]
            else:
                telegram_id = "0"
            try:
                content = build_for_user(telegram_id)
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(content.encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(str(e).encode())
        else:
            self.send_response(200)
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(b"JadeVPN running")

    def do_POST(self):
        if self.path.startswith("/sub") or self.path.startswith("/subscriptions"):
            try:
                content_length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
                data = json.loads(body) if body else {}

                telegram_id = str(data.get("telegram_id") or data.get("telegramId") or data.get("id") or "0")

                subscriptions[telegram_id] = {
                    "created": time.time(),
                    "telegram_id": telegram_id,
                }
                with open(DATA_FILE, "w", encoding="utf-8") as f:
                    json.dump(subscriptions, f, ensure_ascii=False)

                subscription_url = f"{self._base_url()}/subscriptions/{telegram_id}"

                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(
                    json.dumps(
                        {
                            "id": telegram_id,
                            "subscription_id": telegram_id,
                            # In your scheme, the "key" is the subscription link
                            # that contains a list of server keys with names.
                            "key": subscription_url,
                            "subscription_url": subscription_url,
                            "key_list_url": subscription_url,
                        },
                        ensure_ascii=False,
                    ).encode("utf-8")
                )
            except Exception as e:
                self.send_response(500)
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(str(e).encode("utf-8", errors="replace"))
        else:
            self.send_response(404)
            self._send_cors_headers()
            self.end_headers()

print("JadeVPN running: http://0.0.0.0:8000/sub")
HTTPServer(("0.0.0.0", 8000), Handler).serve_forever()
