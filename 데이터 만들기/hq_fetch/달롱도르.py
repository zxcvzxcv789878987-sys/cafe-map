# 달롱도르 본사 공식 매장 목록 받기 (run_all.py가 부른다)
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _hq import *

SOURCE = 'https://dallondor.com/store/find.php'


def fetch():
    L = lines(get(SOURCE))
    i = L.index('개의 매장이 있습니다.')
    return clean((x, L[k + 1]) for k, x in enumerate(L[i:-1], start=i)
                 if '달롱도르' in x and re.search(r'\d', L[k + 1]) and '달롱도르' not in L[k + 1])
