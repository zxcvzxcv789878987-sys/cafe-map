# 프랭크커핀바 본사 공식 매장 목록 (그룹1). run_all.py가 불러 쓴다.
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _g1 import get, clean, flat, done, imweb_list, imweb_boards, g5_array, SKIP

SOURCE = 'http://frankcoffinbar.com/'


def fetch():
    x = flat(get(SOURCE))
    s = x[x.find("매장 안내 |직접검색"):]
    rows = re.findall(r"\|(프랭크커핀바 [^|]+?)\s*\|([^|]+?)\s*\|[0-9\-]*\s*\|-->", s)
    return done(rows, 15)
