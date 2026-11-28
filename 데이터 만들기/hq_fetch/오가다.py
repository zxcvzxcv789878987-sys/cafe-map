# 오가다 본사 공식 매장 목록 (그룹1). run_all.py가 불러 쓴다.
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _g1 import get, clean, flat, done, imweb_list, imweb_boards, g5_array, SKIP

SOURCE = 'http://ogada.co.kr/store/'


def fetch():
    rows = {}
    for p in range(1, 40):
        t = get(SOURCE if p == 1 else SOURCE + "page/%d/" % p)
        items = re.findall(r'<td>\s*<a href="[^"]*\?uid=(\d+)" title="([^"]*)">.*?<td><a href="[^"]*" title="자세히보기">(.*?)</td>', t, re.S)
        new = [i for i in items if i[0] not in rows]
        if not new:
            break
        for i, n, a in new:
            rows[i] = (n, a)
    return done(list(rows.values()), 10)
