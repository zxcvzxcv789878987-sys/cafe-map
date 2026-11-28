# 탐앤탐스 본사 공식 매장 목록 받기 (run_all.py가 부른다)
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _hq import *

SOURCE = 'https://www.tomntoms.com/store'


def fetch():
    d = get_json('https://www.tomntoms.com/api/v1/store/domestic')['data']['elements']
    return clean((x['title'], ((x['roadAddress'] or x['jibunAddress'] or '') + ' ' + (x['detailAddress'] or '')).strip()) for x in d)
