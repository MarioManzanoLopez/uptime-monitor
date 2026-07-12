import requests
import time

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def check_site(url: str):
    start = time.time()
    try:
        r = requests.get(url, timeout=10, headers=HEADERS)
        response_time = round(time.time() - start, 3)
        return {
            "status": "up" if 200 <= r.status_code < 400 else "down",
            "status_code": r.status_code,
            "response_time": response_time
        }
    except requests.exceptions.RequestException:
        return {
            "status": "down",
            "status_code": None,
            "response_time": None
        }