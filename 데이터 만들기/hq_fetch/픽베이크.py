# 픽베이크 본사 공식 매장 목록 받기 (run_all.py가 부른다)
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _hq import *

SOURCE = 'https://www.pickbake.co.kr/40'


def fetch():
    L = lines(get(SOURCE))
    rows = []
    for i, x in enumerate(L[:-1]):
        if not x.startswith('픽베이크 ') or '~' in x:
            continue
        a = L[i + 1]
        if (i + 2 < len(L) and not L[i + 2].startswith(('픽베이크', 'Tel')) and len(L[i + 2]) < 25
                and re.search(r'(호|층|프라자|빌딩|동)$', L[i + 2])):
            a += ' ' + L[i + 2]
        rows.append((x, a))
    return clean(rows)
