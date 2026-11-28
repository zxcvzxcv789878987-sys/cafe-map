# 요거보라 본사 공식 매장 목록 (그룹1). run_all.py가 불러 쓴다.
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _g1 import get, clean, flat, done, imweb_list, imweb_boards, g5_array, SKIP

SOURCE = 'https://www.yogurtbora.co.kr/store'


def fetch():
    rows, skipped = {}, set()
    for p in range(1, 60):
        t = get(SOURCE + "/?page=%d" % p)
        i = t.find('id="post_card_')
        if i < 0:
            break
        x = flat(t[i:t.find("FAMILY SITE", i)])
        items = re.findall(r"\|(요거보라[^|]*?)\s*\|(?:--> \|)*\* 주소 :(.*?)\* 전화번호", x)
        new = [it for it in items if it[0].strip() not in rows and it[0].strip() not in skipped]
        if not new:
            break
        for n, a in new:
            n = n.strip()
            if re.search(r"오픈\s*예정|준비", n):
                skipped.add(n)
            else:
                rows[n] = (n, a)
    return done(list(rows.values()), 15)
