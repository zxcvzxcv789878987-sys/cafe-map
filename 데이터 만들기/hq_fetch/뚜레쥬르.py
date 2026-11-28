# 뚜레쥬르 본사 공식 매장 목록 받기 (run_all.py가 부른다)
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _hq import *

SOURCE = 'https://www.tlj.co.kr/store/search.asp'


def fetch():
    rows = []
    for p in range(1, 400):
        h = get(SOURCE + '?page=%d' % p)
        r = re.findall(r'id="listName_(\d+)">.*?smallPop\(\d+\);">(.*?)</a>.*?id="listAddrD_\1">(.*?)</span>'
                       r'.*?id="listAddrJ_\1">(.*?)</span>', h, re.S)
        if not r:
            break
        rows += [(n, txt(a) or txt(j)) for _, n, a, j in r]
    return clean(rows)
