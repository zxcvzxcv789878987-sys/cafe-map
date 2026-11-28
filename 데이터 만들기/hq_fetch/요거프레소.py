# 요거프레소 본사 공식 매장 목록 받기 (run_all.py가 부른다)
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _hq import *

SOURCE = 'https://www.yogerpresso.co.kr/store/store.html'


def fetch():
    d = get_json('https://www.yogerpresso.co.kr/INC/func_other_ajax.php', {'mode': 'map_search'},
                 {'Referer': SOURCE})
    return clean((x['title'], x['uaddr1']) for x in d['msg'])
