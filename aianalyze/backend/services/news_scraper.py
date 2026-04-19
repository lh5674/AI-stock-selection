import requests
import random
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
}

def get_finance_news(limit: int = 5):
    """
    中文财经新闻源（新加坡可访问）:
    1. 新浪财经 RSS
    2. 36氪 RSS
    3. 华尔街见闻 RSS
    每次随机打乱，返回不同的5条
    """
    all_news = []

    # ── 1. 新浪财经 RSS ──────────────────────────────────────
    try:
        r = requests.get(
            "https://feed.mix.sina.com.cn/api/roll/get?pageid=153&lid=2516&k=&num=50&page=1&r=0.5",
            headers=HEADERS, timeout=8
        )
        data = r.json()
        for item in data.get("result", {}).get("data", []):
            title = item.get("title", "").strip()
            url   = item.get("url", "#")
            time  = item.get("ctime", "")
            if title:
                all_news.append({"title": title, "time": time, "url": url, "source": "新浪财经"})
        print(f"[news] 新浪财经 OK — {len(all_news)} items")
    except Exception as e:
        print(f"[news] 新浪财经 failed: {e}")

    # ── 2. 36氪 RSS ──────────────────────────────────────────
    try:
        r = requests.get(
            "https://36kr.com/feed",
            headers=HEADERS, timeout=8
        )
        soup = BeautifulSoup(r.content, "xml")
        for item in soup.find_all("item")[:20]:
            title = item.find("title")
            link  = item.find("link")
            pub   = item.find("pubDate")
            if title and title.text.strip():
                all_news.append({
                    "title":  title.text.strip(),
                    "time":   pub.text.strip()[:25] if pub else "",
                    "url":    link.text.strip() if link else "#",
                    "source": "36氪"
                })
        print(f"[news] 36氪 OK")
    except Exception as e:
        print(f"[news] 36氪 failed: {e}")

    # ── 3. 华尔街见闻 RSS ────────────────────────────────────
    try:
        r = requests.get(
            "https://wallstreetcn.com/rss.xml",
            headers=HEADERS, timeout=8
        )
        soup = BeautifulSoup(r.content, "xml")
        for item in soup.find_all("item")[:20]:
            title = item.find("title")
            link  = item.find("link")
            pub   = item.find("pubDate")
            if title and title.text.strip():
                all_news.append({
                    "title":  title.text.strip(),
                    "time":   pub.text.strip()[:25] if pub else "",
                    "url":    link.text.strip() if link else "#",
                    "source": "华尔街见闻"
                })
        print(f"[news] 华尔街见闻 OK")
    except Exception as e:
        print(f"[news] 华尔街见闻 failed: {e}")

    # ── 4. 备用：雪球 RSS ────────────────────────────────────
    if len(all_news) < limit:
        try:
            r = requests.get(
                "https://xueqiu.com/hots.json?count=20",
                headers={**HEADERS, "Cookie": "xq_a_token=;"},
                timeout=8
            )
            data = r.json()
            for item in data.get("list", [])[:20]:
                title = item.get("title", "").strip()
                if title:
                    all_news.append({
                        "title":  title,
                        "time":   "",
                        "url":    f"https://xueqiu.com{item.get('target', '')}",
                        "source": "雪球"
                    })
            print(f"[news] 雪球 OK")
        except Exception as e:
            print(f"[news] 雪球 failed: {e}")

    if not all_news:
        print("[news] All Chinese sources failed")
        return []

    # 每次随机打乱，返回不同的5条
    random.shuffle(all_news)
    result = all_news[:limit]
    print(f"[news] returning {len(result)} random items from {len(all_news)} total")
    return result