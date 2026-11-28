# 벤티프레소 본사 공식 매장 목록 받기 (run_all.py가 부른다)
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _hq import *

SOURCE = 'https://www.ventipresso.co.kr/venti/board?bo_table=shopinfo'


def fetch():
    rows = []
    for p in range(1, 100):
        L = lines(get(SOURCE + '&page=%d' % p))
        new = [(x, L[i + 1]) for i, x in enumerate(L[:-1]) if x.startswith('벤티프레소 ') and re.search(r'\d', L[i + 1])]
        new = [x for x in new if x not in rows]
        if not new:
            break
        rows += new
    return clean(rows)
