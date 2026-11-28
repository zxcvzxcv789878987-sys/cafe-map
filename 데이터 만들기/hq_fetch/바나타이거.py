# 바나타이거 본사 공식 매장 목록 받기 (run_all.py가 부른다)
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _hq import *

SOURCE = 'https://www.banatiger.co.kr/html/store.asp'


def fetch():
    d = get_json('https://www.banatiger.co.kr/common/ajax/ajaxStore.asp',
                 {'cmd': 'getList', 'idx': '', 'city': '', 'state': '', 'storeOrAddr': '', 'page': 1, 'pageListCnt': 3000},
                 {'Referer': SOURCE})
    return clean((x['storeNm'], x['address']) for x in d['dataList'] if x.get('part', 'open') == 'open')
