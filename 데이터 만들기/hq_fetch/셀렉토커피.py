# 셀렉토커피 본사 공식 매장 목록 받기 (run_all.py가 부른다)
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _hq import *

SOURCE = 'https://www.selecto.co.kr/brand/store_search.asp'


def fetch():
    d = get_json('https://www.selecto.co.kr/brand/ajaxBrand.asp',
                 {'cmd': 'getStoreList', 'part': 'open', 'city': '', 'state': '', 'store_nm': '',
                  'searchOpt': '', 'page': 1, 'pageSize': 3000}, {'Referer': SOURCE})
    return clean((x['store_nm'], x['addr1'] + ' ' + x['addr2']) for x in d['dataList'])
