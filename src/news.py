"""News headlines from Google News RSS (India edition), month by month.

Yahoo has no usable news feed for NSE tickers, so Google News is the primary
source. Each monthly query returns at most 100 items, so a year of coverage
takes 12 requests per company. Headlines only: full articles are often paywalled.
"""
from __future__ import annotations

import time
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import date

import pandas as pd
import requests

RSS = "https://news.google.com/rss/search?"
# Market terms keep the feed to investor-relevant stories (not prizes, CSR, sport).
MARKET_TERMS = "(shares OR stock OR results OR profit OR revenue OR target OR brokerage OR rating)"


def month_starts(end: date, months: int) -> list[date]:
    """First day of each of the last `months` months, oldest first, ending with end's month."""
    first = date(end.year, end.month, 1)
    out = []
    for i in range(months):
        y, m = divmod(first.month - 1 - i, 12)
        out.append(date(first.year + y, m + 1, 1))
    return out[::-1]


def _next_month(d: date) -> date:
    return date(d.year + d.month // 12, d.month % 12 + 1, 1)


def fetch_month(name: str, start: date, verify) -> list[dict]:
    q = f'"{name}" {MARKET_TERMS} after:{start.isoformat()} before:{_next_month(start).isoformat()}'
    url = RSS + urllib.parse.urlencode({"q": q, "hl": "en-IN", "gl": "IN", "ceid": "IN:en"})
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, verify=verify, timeout=30)
    r.raise_for_status()
    rows = []
    for item in ET.fromstring(r.content).findall("./channel/item"):
        source = item.findtext("source") or ""
        title = item.findtext("title") or ""
        if source and title.endswith(f" - {source}"):
            title = title[: -len(source) - 3]          # Google appends " - Publisher"
        rows.append({"published": item.findtext("pubDate"), "title": title.strip(), "source": source,
                     "link": item.findtext("link")})
    return rows


def fetch_headlines(companies: dict[str, str], end: date, months: int, verify, pause: float = 1.0) -> pd.DataFrame:
    """Headlines for {ticker: company name} over the last `months` months, de-duplicated."""
    rows = []
    for ticker, name in companies.items():
        for start in month_starts(end, months):
            for row in fetch_month(name, start, verify):
                rows.append({"ticker": ticker, **row})
            time.sleep(pause)
    df = pd.DataFrame(rows)
    df["published"] = pd.to_datetime(df["published"], utc=True).dt.tz_convert("Asia/Kolkata").dt.tz_localize(None)
    df = df.drop_duplicates(subset=["ticker", "title"]).sort_values(["ticker", "published"])
    return df.reset_index(drop=True)
