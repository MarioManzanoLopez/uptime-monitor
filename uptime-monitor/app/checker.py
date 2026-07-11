import requests
import time

def check_site(url: str):
    start = time.time()
    try:
        r = requests.get(url, timeout=10)
        response_time = round(time.time() - start, 3)
        return {
            "status": "up" if r.status_code == 200 else "down",
            "status_code": r.status_code,
            "response_time": response_time
        }
    except requests.exceptions.RequestException:
        return {
            "status": "down",
            "status_code": None,
            "response_time": None
        }