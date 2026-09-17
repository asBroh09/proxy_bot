# checker.py
import concurrent.futures
import socket
import time
import requests

try:
    import socks
except ImportError:
    socks = None


def get_country(ip):
    """ip-api.com থেকে দেশ বের করে (ফ্রি, ৪৫ req/min)"""
    try:
        r = requests.get(f"http://ip-api.com/json/{ip}", timeout=3)
        data = r.json()
        if data.get("status") == "success":
            return data.get("country", "Unknown")
    except Exception:
        pass
    return "Unknown"


def check_http(proxy, site, timeout):
    """HTTP/HTTPS প্রক্সি চেক"""
    try:
        proxies = {"http": f"http://{proxy}", "https": f"http://{proxy}"}
        start = time.time()
        r = requests.get(site, proxies=proxies, timeout=timeout,
                         headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code < 400:
            return True, int((time.time() - start) * 1000)
    except Exception:
        pass
    return False, 0


def check_socks(proxy, site, timeout, version):
    """SOCKS4/5 প্রক্সি চেক"""
    if socks is None:
        return False, 0
    ip, port = proxy.split(":")
    try:
        s = socks.socksocket()
        s.set_proxy(socks.SOCKS4 if version == "socks4" else socks.SOCKS5,
                    ip, int(port))
        s.settimeout(timeout)
        start = time.time()
        s.connect((site.replace("https://", "").replace("http://", "").split("/")[0], 80))
        elapsed = int((time.time() - start) * 1000)
        s.close()
        return True, elapsed
    except Exception:
        return False, 0


def check_one(proxy, method, site, timeout):
    """একটা প্রক্সি চেক করে result dict রিটার্ন করে"""
    if method in ("http", "https"):
        ok, ping = check_http(proxy, site, timeout)
    else:
        ok, ping = check_socks(proxy, site, timeout, method)

    if not ok:
        return None

    ip = proxy.split(":")[0]
    country = get_country(ip)

    return {
        "proxy": proxy,
        "method": method,
        "country": country,
        "ping": ping,
    }


def check_bulk(proxies, method, site, timeout, max_workers, progress_cb=None):
    """একসাথে অনেক প্রক্সি চেক করে। progress_cb(done, total, live) কল হয়।"""
    live = []
    done = 0
    total = len(proxies)

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(check_one, p, method, site, timeout): p for p in proxies}
        for fut in concurrent.futures.as_completed(futures):
            done += 1
            try:
                res = fut.result()
                if res:
                    live.append(res)
            except Exception:
                pass
            if progress_cb and (done % 50 == 0 or done == total):
                progress_cb(done, total, len(live))

    return live
