# 블루보틀 본사 공식 매장 목록 받기 (run_all.py가 부른다)
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _hq import *

SOURCE = 'https://kr.bluebottlecoffee.com/pages/cafe-list'


def fetch():
    L = lines(get(SOURCE))
    return clean((L[k - 1], x) for k, x in enumerate(L) if k and re.match(REGION, x) and '블루보틀' in L[k - 1])
