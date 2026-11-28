# 위클리베이글 본사 공식 매장 목록 (그룹1). run_all.py가 불러 쓴다.
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _g1 import get, clean, flat, done, imweb_list, imweb_boards, g5_array, SKIP

SOURCE = 'https://www.weeklybagel.co.kr/#doz_menu_store'


def fetch():
    t = get("https://www.weeklybagel.co.kr")
    rows = []
    for b in imweb_boards(t):
        rows += imweb_list("https://www.weeklybagel.co.kr", b, "https://www.weeklybagel.co.kr")
    return done(rows, 8)
