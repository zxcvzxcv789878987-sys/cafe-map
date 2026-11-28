# 카페051 본사 공식 매장 목록 받기 (run_all.py가 부른다)
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _hq import *

SOURCE = 'https://cafe051.com/findstore'


def fetch():
    rows = []
    for p in range(1, 100):
        d = get_json('https://cafe051.com/', {'module': 'storemap', 'act': 'procStoremapGetItemList',
                     'page': p, 'mid': 'findstore', 'search_keyword': ''},
                     {'X-Requested-With': 'XMLHttpRequest', 'Accept': 'application/json', 'Referer': SOURCE})
        r = re.findall(r'item_title">(.*?)</div>\s*<div class="item_address">(.*?)</div>', d.get('result') or '', re.S)
        new = [x for x in r if x not in rows]
        if not new:
            break
        rows += new
    return clean(rows)
