# 바스타커피 본사 공식 매장 목록 (그룹1). run_all.py가 불러 쓴다.
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _g1 import get, clean, flat, done, imweb_list, imweb_boards, g5_array, SKIP

SOURCE = 'http://www.bastacoffee.com/bbs/board.php?bo_table=store'


def fetch():
    x = flat(get(SOURCE))
    rows = []
    for seg in x.split("자세히 보기")[:-1]:
        m = re.search(r"\|\d+ \|[^|]+\|([^|]+)\|([^|]+)\|", seg[-400:])
        if m:
            rows.append(m.groups())
    return done(rows, 5)
