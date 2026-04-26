from http.server import BaseHTTPRequestHandler, HTTPServer
import time
import base64
import requests

SOURCE = "https://tiagorrg.github.io/vless-checker/keys.json"

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

def best_latency(nodes):
    """
    выбираем сервер с минимальной latency
    """
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
    """
    собираем country + w_country
    """
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
    data = requests.get(SOURCE, timeout=10).json()

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
    announce = base64.b64encode("Welcome to XAMVPN 🚀".encode()).decode()
    expire = int(time.time()) + 30 * 24 * 60 * 60
    date = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())

    out = ""
    out += "# profile-title: 🟦 XAMVPN 🟦\n"
    out += "# profile-update-interval: 5\n"
    out += "# support-url: https://t.me/XAMVPN\n"
    out += "# profile-web-page-url: https://xamvpn.local\n"
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


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/sub"):
            try:
                content = build()

                self.send_response(200)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.end_headers()

                self.wfile.write(content.encode("utf-8"))

            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(e).encode())
        else:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"XAMVPN running")


print("XAMVPN running: http://0.0.0.0:8000/sub")

HTTPServer(("0.0.0.0", 8000), Handler).serve_forever()
