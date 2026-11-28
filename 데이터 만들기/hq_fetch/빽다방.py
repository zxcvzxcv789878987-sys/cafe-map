# 빽다방 본사 공식 매장 목록 받기 (run_all.py가 부른다)
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _hq import *

SOURCE = 'https://paikdabang.com/store/'


def fetch():
    api = 'https://theborndb.theborn.co.kr/wp-json/api/get_store/?state=9&category=275&depth1=&depth2=&search_string=&paged='
    rows = []
    for p in range(1, 400):
        r = get_json(api + str(p)).get('results') or []
        if not r:
            break
        rows += [(re.sub(r'\s*MINI$', '', txt(x['store_name'])), x['store_address']) for x in r]
    return clean(rows)
