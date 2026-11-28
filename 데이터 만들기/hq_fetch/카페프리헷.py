# 카페프리헷 본사 공식 매장 목록 받기 (run_all.py가 부른다)
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _hq import *

SOURCE = 'https://www.cafefrihet.com/bbs/board.php?bo_table=branch'


def fetch():
    L = lines(get(SOURCE))
    return clean((x, L[i + 1]) for i, x in enumerate(L[:-1]) if x.startswith('카페프리헷 ') and re.search(r'\d', L[i + 1]))
