# 블루샥 본사 공식 매장 목록 (그룹1). run_all.py가 불러 쓴다.
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _g1 import get, clean, flat, done, imweb_list, imweb_boards, g5_array, SKIP

SOURCE = 'https://www.blushaak.co.kr/store'


def fetch():
    t = get(SOURCE)
    rows = re.findall(r'<h3 class="text-lg font-semibold text-dark-800">(.*?)</h3>.*?</svg><span>(.*?)</span>', t, re.S)
    return done(rows, 100)
