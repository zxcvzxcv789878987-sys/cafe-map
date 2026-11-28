# 파리크라상 본사 공식 매장 목록 받기 (run_all.py가 부른다)
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _hq import *

SOURCE = 'https://www.pariscroissant.co.kr/board/findstore/list.html?board_no=1002'


def fetch():
    rows = []
    for p in range(1, 30):
        L = lines(get(SOURCE + '&page=%d' % p))
        new = [(L[i - 2], L[i - 1]) for i, x in enumerate(L) if i > 1 and x.startswith('전화번호 :')]
        new = [x for x in new if x not in rows]
        if not new:
            break
        rows += new
    return clean(rows)
