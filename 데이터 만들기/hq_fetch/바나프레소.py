# 바나프레소 본사 공식 매장 목록 받기 (run_all.py가 부른다)
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _hq import *

SOURCE = 'https://www.banapresso.com/store'


def fetch():
    h = get(SOURCE)
    dec = json.JSONDecoder()
    rows = []
    for m in re.finditer(r'\{"fc":\d+,"n":', h):
        o = dec.raw_decode(h, m.start())[0]
        n = o['n'] if o['n'].endswith('점') else o['n'] + '점'
        rows.append((n, o['a']))
    return clean(rows)
