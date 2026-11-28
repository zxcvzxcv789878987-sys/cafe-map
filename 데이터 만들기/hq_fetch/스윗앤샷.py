# 스윗앤샷 본사 공식 매장 목록 받기 (run_all.py가 부른다)
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _hq import *

SOURCE = 'https://www.snscoffee.co.kr/store'


def fetch():
    L = lines(get(SOURCE))
    rows = []
    for k, x in enumerate(L):
        if k and re.match(REGION, x) and re.search(r'\d', x):
            n = L[k - 1]
            if (n.endswith('점') or not re.match(REGION, n)) and len(n) < 30 and not re.search(r'\d{2,}', n):
                rows.append((n, x))
    return clean(rows)
