from http.server import BaseHTTPRequestHandler, HTTPServer
import json
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
    "russia": "Россия"
}

def get_best(block):
    if not block:
        return None
    if "best" in block:
        return block["best"]
    if "top10" in block and len(block["top10"]) > 0:
        return block["top10"][0]["key"]
    return None

def clean(key, name):
    return key.split("#")[0] + "#" + name

def build_subscription():
    data = requests.get(SOURCE, timeout=10).json()

    result = []

    # priority
    for c in PRIORITY:
        if c in data:
            k = get_best(data[c])
            if k:
                result.append((c, k, False))

    # others
    for c in data:
        if c == "updated_at":
            continue
        if c in PRIORITY:
            continue

        k = get_best(data[c])
        if k:
            result.append((c, k, False))

    # whitelist (Russia)
    if "russia" in data:
        k = get_best(data["russia"])
        if k:
            result.append(("russia", k, True))

    # header
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
        name = "Белые списки" if white else RU.get(c, c)
        out += clean(k, name) + "\n"

    return out


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/sub"):
            try:
                content = build_subscription()
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.end_headers()
                self.wfile.write(content.encode())
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(e).encode())
        else:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"XAMVPN server running")


print("XAMVPN running on http://0.0.0.0:8000/sub")

HTTPServer(("0.0.0.0", 8000), Handler).serve_forever()
