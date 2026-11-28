# 백금당 본사 공식 매장 목록 받기 (run_all.py가 부른다)
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _hq import *

SOURCE = 'https://www.baekgeumdang.com/store'


def fetch():
    L = lines(get(SOURCE))
    i = L.index('본점')
    rows = []
    for k in range(i, len(L)):
        x = L[k]
        if '모집중' in x:
            break
        # 주소 줄: 숫자와 시군구가 있고 '호점'이 없는 줄
        if re.search(r'\d', x) and re.search(r'[시구군] ', x) and '호점' not in x:
            prev = L[k - 1]
            if re.search(r'\d', prev) and re.search(r'[시구군] ', prev):
                continue   # 같은 매장의 둘째 주소(지번)
            name = re.sub(r'\d+호점|본점|\|', ' ', prev).strip()
            if name:
                rows.append((name, x))
    return clean(rows)
