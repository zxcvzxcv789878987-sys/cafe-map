# 히얼이즈커피 본사 공식 매장 목록 (그룹1). run_all.py가 불러 쓴다.
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _g1 import get, clean, flat, done, imweb_list, imweb_boards, g5_array, SKIP

SOURCE = 'https://www.hereiscoffee.com/store/store'


def fetch():
    t = re.sub(r"<!--.*?-->", "", get(SOURCE), flags=re.S)
    rows = re.findall(r'<div class="store-box">.*?<h4>(.*?)</h4>.*?<span>주소</span><p>(.*?)</p>', t, re.S)
    return done(rows, 8)
