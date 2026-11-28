# 트리플에이커피 본사 공식 매장 목록 받기 (run_all.py가 부른다)
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _hq import *

SOURCE = 'https://tripleacoffee.co.kr/store/store.html'


def fetch():
    def url(p):
        return SOURCE if p == 1 else 'https://tripleacoffee.co.kr/store/store__p%d.html' % p
    rows = []
    for p in range(1, 100):
        try:
            h = get(url(p))
        except Exception:
            if p == 1:
                raise
            break
        new = [(txt(a), txt(b)) for a, b in re.findall(r'<td>([^<]*)</td>\s*<td><a href="/store/store-view__\d+\.html">(.*?)</a>', h, re.S)]
        new = [x for x in new if x not in rows]
        if not new:
            break
        rows += new
    return clean(rows)
