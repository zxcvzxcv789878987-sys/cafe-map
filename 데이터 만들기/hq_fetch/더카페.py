# 더카페 본사 공식 매장 목록 받기 (run_all.py가 부른다)
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _hq import *

SOURCE = 'https://thecaffeopen.com/#Store'


def fetch():
    h = get('https://thecaffeopen.com/theme/thecaffe/MainLatestLoad.php',
            {'search': '', 'page': 1, 'itemsPerPage': 3000})
    L = lines(h)
    return clean((L[i][3:], L[i + 1][3:]) for i in range(len(L) - 1)
                 if L[i].startswith('지점:') and L[i + 1].startswith('주소:'))
