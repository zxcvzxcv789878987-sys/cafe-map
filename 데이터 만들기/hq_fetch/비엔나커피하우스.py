# 비엔나커피하우스 본사 공식 매장 목록 (그룹1). run_all.py가 불러 쓴다.
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _g1 import get, clean, flat, done, imweb_list, imweb_boards, g5_array, SKIP

SOURCE = 'https://viennacoffeehouse.co.kr/stores'


def fetch():
    def parse(h):
        return re.findall(r'stores/view/(\d+)".*?<h3[^>]*>(.*?)</h3>.*?<path d="M20 10c0[^>]*/>.*?</svg>\s*<span>(.*?)</span>', h, re.S)
    rows = {i: (n, a) for i, n, a in parse(get(SOURCE))}
    for p in range(2, 40):
        d = json.loads(get(SOURCE + "/load-more?page=%d" % p, headers={"X-Requested-With": "XMLHttpRequest", "Referer": SOURCE}))
        if not d.get("success") or not d.get("html"):
            break
        new = [x for x in parse(d["html"]) if x[0] not in rows]
        if not new:
            break
        for i, n, a in new:
            rows[i] = (n, a)
        if not d.get("hasMore", True):
            break
    return done(list(rows.values()), 5)
