# 더벤티 본사 공식 매장 목록 (그룹1). run_all.py가 불러 쓴다.
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _g1 import get, clean, flat, done, imweb_list, imweb_boards, g5_array, SKIP

SOURCE = 'https://www.theventi.co.kr/new2022/store/index.html'


def fetch():
    t = get(SOURCE + "?page=1&plist=3000")
    rows = re.findall(r'<p class="tit_b _mc">(.*?)</p>.*?<div class="address">(.*?)</div>', t, re.S)
    return done(rows, 500)
