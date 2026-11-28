# 커피나인 본사 공식 매장 목록 받기 (run_all.py가 부른다)
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _hq import *

SOURCE = 'https://coffee9.co.kr/stores'


def fetch():
    L = lines(get(SOURCE))
    rows = []
    for i, x in enumerate(L):
        if i < 3 or not re.match(REGION, x):
            continue
        if 'coming soon' in (L[i - 2] + L[i - 3]).lower():
            continue
        if L[i - 1].endswith('점'):
            rows.append((L[i - 1], x))
        elif L[i - 2] == '커피나인':
            rows.append((L[i - 1] + '점', x))
    return clean(rows)
