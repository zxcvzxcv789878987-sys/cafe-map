# 만랩커피 본사 공식 매장 목록 (그룹1). run_all.py가 불러 쓴다.
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _g1 import get, clean, flat, done, imweb_list, imweb_boards, g5_array, SKIP

SOURCE = 'https://www.10000lab.com/59'


def fetch():
    rows = []
    for b in imweb_boards(get(SOURCE)):
        rows += imweb_list('https://www.10000lab.com', b, SOURCE)
    return done(rows, 25)
