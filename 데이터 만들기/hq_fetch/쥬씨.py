# 쥬씨 본사 공식 매장 목록 받기 (run_all.py가 부른다)
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _hq import *

SOURCE = 'http://www.no1juicy.com/franchise/findStore'


def fetch():
    d = get_json('http://www.no1juicy.com/franchise/getStoreList')
    return clean((x['franchise_name'], x['addr_name']) for x in d if x.get('status') == 'YES')
