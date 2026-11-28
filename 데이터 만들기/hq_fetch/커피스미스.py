# 커피스미스 본사 공식 매장 목록 받기 (run_all.py가 부른다)
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _hq import *

SOURCE = 'http://coffeesmith.co.kr/branch/'


def fetch():
    h = get(SOURCE)
    items = re.findall(r'<li itemscope[^>]*class="([^"]*)".*?<h3 class="post-title"><a href="([^"]+)">(.*?)</a>', h, re.S)
    rows = []
    for cls, u, name in items:
        if 'overseas' in cls:
            continue
        L = lines(get(u))
        if 'ADDRESS' in L:
            a = L[L.index('ADDRESS') + 1]
            if a != 'TEL' and re.search(r'\d', a):   # 문 닫은 지점은 주소 칸이 비어 있다
                rows.append((name, a))
    return clean(rows)
