# 카페일리터 본사 공식 매장 목록 받기 (run_all.py가 부른다)
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _hq import *

SOURCE = 'https://cafe1liter.com/지점-안내/'


def fetch():
    base = 'https://cafe1liter.com/%ec%a7%80%ec%a0%90-%ec%95%88%eb%82%b4/?jsf=jet-engine&pagenum='
    rows = []
    for p in range(1, 60):
        L = lines(get(base + str(p)))
        r = [(L[i - 1], x) for i, x in enumerate(L) if i and L[i - 1].endswith('점') and len(L[i - 1]) < 25
             and re.search(r'\d', x) and ' ' in x and len(x) > 8]
        new = [x for x in r if x not in rows]
        if not new:
            break
        rows += new
    return clean(rows)
