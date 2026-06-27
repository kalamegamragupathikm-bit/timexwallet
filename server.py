#!/usr/bin/env python3
import json
import os
import time
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

PORT = int(os.environ.get("TIMEWALLET_PORT", "43128"))
ROOT = os.path.dirname(os.path.abspath(__file__))
RATE_CACHE = {"expires": 0, "data": None}


def wise_quote(source, target):
    payload = json.dumps({
        "sourceCurrency": source,
        "targetCurrency": target,
        "sourceAmount": 1,
    }).encode("utf-8")
    request = urllib.request.Request(
        "https://api.wise.com/v3/quotes",
        data=payload,
        headers={"Content-Type": "application/json", "User-Agent": "Timewallet/2.0"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=12) as response:
        return json.loads(response.read().decode("utf-8"))


def market_rates():
    request = urllib.request.Request(
        "https://fxapi.app/api/usd.json",
        headers={"Accept": "application/json", "User-Agent": "Timewallet/2.0"},
    )
    with urllib.request.urlopen(request, timeout=12) as response:
        return json.loads(response.read().decode("utf-8"))


def current_rates():
    if RATE_CACHE["data"] and time.time() < RATE_CACHE["expires"]:
        return RATE_CACHE["data"]
    usd_inr = wise_quote("USD", "INR")
    ils_inr = wise_quote("ILS", "INR")
    market = market_rates()
    rates = dict(market.get("rates", {}))
    rates["USD"] = 1
    rates["INR"] = usd_inr["rate"]
    rates["ILS"] = usd_inr["rate"] / ils_inr["rate"]
    result = {
        "provider": "Wise + live market",
        "timestamp": usd_inr.get("createdTime") or market.get("timestamp"),
        "rates": rates,
        "wisePairs": {"USD_INR": usd_inr["rate"], "ILS_INR": ils_inr["rate"]},
    }
    RATE_CACHE.update(expires=time.time() + 55, data=result)
    return result


class TimewalletHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path.split("?", 1)[0] == "/api/wise-rates":
            try:
                body = json.dumps(current_rates()).encode("utf-8")
                self.send_response(200)
            except Exception as error:
                body = json.dumps({"error": "Wise rate unavailable", "detail": str(error)}).encode("utf-8")
                self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        super().do_GET()


if __name__ == "__main__":
    os.chdir(ROOT)
    print(f"Timewallet 2.0 running at http://127.0.0.1:{PORT}")
    ThreadingHTTPServer(("127.0.0.1", PORT), TimewalletHandler).serve_forever()
