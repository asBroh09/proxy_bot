# scraper.py
import asyncio
import re
import httpx
from bs4 import BeautifulSoup

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"


class Scraper:
    def __init__(self, method, url):
        self.method = method
        self.url = url

    async def scrape(self, client):
        try:
            r = await client.get(self.url, timeout=15, headers={"User-Agent": UA})
            return self._parse(r.text)
        except Exception:
            return []

    def _parse(self, text):
        pattern = re.compile(r"\d{1,3}(?:\.\d{1,3}){3}:\d{1,5}")
        return re.findall(pattern, text)


class TableScraper(Scraper):
    async def scrape(self, client):
        try:
            r = await client.get(self.url, timeout=15, headers={"User-Agent": UA})
            soup = BeautifulSoup(r.text, "html.parser")
            proxies = set()
            table = soup.find("table")
            if not table:
                return []
            for row in table.find_all("tr"):
                cells = row.find_all("td")
                if len(cells) >= 2:
                    ip = cells[0].text.strip()
                    port = cells[1].text.strip()
                    if re.match(r"\d{1,3}(?:\.\d{1,3}){3}$", ip) and port.isdigit():
                        proxies.add(f"{ip}:{port}")
            return list(proxies)
        except Exception:
            return []


SOURCES = {
    "http": [
        "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/all/data.txt",
        "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
        "https://raw.githubusercontent.com/zloi-user/hideip.me/main/http.txt",
        "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
        "https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=5000",
        "https://spys.me/proxy.txt",
    ],
    "socks4": [
        "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks4.txt",
        "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks4.txt",
        "https://raw.githubusercontent.com/zloi-user/hideip.me/main/socks4.txt",
        "https://api.proxyscrape.com/v2/?request=getproxies&protocol=socks4&timeout=5000",
    ],
    "socks5": [
        "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt",
        "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks5.txt",
        "https://raw.githubusercontent.com/zloi-user/hideip.me/main/socks5.txt",
        "https://api.proxyscrape.com/v2/?request=getproxies&protocol=socks5&timeout=5000",
    ],
}


async def scrape_all(method):
    """method: http / socks4 / socks5 / all"""
    methods = ["http", "socks4", "socks5"] if method == "all" else [method]
    urls = []
    for m in methods:
        for u in SOURCES.get(m, []):
            urls.append((m, u))

    async with httpx.AsyncClient(follow_redirects=True) as client:
        tasks = [Scraper(m, u).scrape(client) for m, u in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    proxies = set()
    for res in results:
        if isinstance(res, list):
            for p in res:
                proxies.add(p)

    return list(proxies)
