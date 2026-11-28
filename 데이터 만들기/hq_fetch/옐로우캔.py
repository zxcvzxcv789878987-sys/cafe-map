# 옐로우캔 본사 공식 매장 목록 (그룹1). run_all.py가 불러 쓴다.
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _g1 import get, clean, flat, done, imweb_list, imweb_boards, g5_array, SKIP

SOURCE = 'https://www.yellowcan.co.kr/home/c/Store'


def fetch():
    rows, seen = [], set()
    for p in range(1, 40):
        t = get("https://www.yellowcan.co.kr/?c=Store&p=%d" % p)
        items = re.findall(r'<tr id="item-(\d+)">\s*<td[^>]*>.*?</td>\s*<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>', t, re.S)
        new = [i for i in items if i[0] not in seen]
        if not new:
            break
        for uid, n, a, tel in new:
            seen.add(uid)
            if not re.search(SKIP, clean(tel) + clean(n)):
                rows.append((n, a))
    return done(rows, 10)
