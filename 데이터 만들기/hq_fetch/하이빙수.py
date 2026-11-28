# 하이빙수 본사 공식 매장 목록 받기 (run_all.py가 부른다)
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _hq import *

SOURCE = 'https://www.highbingsu.co.kr/'


def fetch():
    h = get('https://www.highbingsu.co.kr/ajax/ajax.areaList_25.php', {'page': 1, 'area': '', 'keyword': ''},
            {'X-Requested-With': 'XMLHttpRequest', 'Referer': SOURCE})
    return clean(re.findall(r'<h1>(.*?)</h1>\s*<p>(.*?)</p>', h, re.S))
