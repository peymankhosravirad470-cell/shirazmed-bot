# news_test.py
import requests

def run_news_test():
    print("=" * 40)
    print("NEWS_TEST: starting")
    print("=" * 40)
    urls = [
        ("ISNA all", "https://www.isna.ir/rss"),
        ("ISNA health", "https://www.isna.ir/rss/tp/14"),
        ("Mehr all", "https://www.mehrnews.com/rss"),
        ("Mehr health", "https://www.mehrnews.com/rss/tp/153"),
        ("IRNA all", "https://www.irna.ir/rss"),
        ("IRNA health", "https://www.irna.ir/rss/tp/24"),
        ("Fars news", "https://www.farsnews.ir/rss"),
    ]
    for name, url in urls:
        try:
            r = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
            text_len = len(r.text) if r.text else 0
            has_xml = "<rss" in (r.text or "").lower() or "<feed" in (r.text or "").lower()
            print("NEWS_TEST_RESULT | " + name + " | status=" + str(r.status_code) + " | len=" + str(text_len) + " | xml=" + str(has_xml))
        except Exception as e:
            print("NEWS_TEST_RESULT | " + name + " | ERROR=" + str(e))
    print("NEWS_TEST: done")