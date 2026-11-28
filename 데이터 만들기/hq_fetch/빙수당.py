# 빙수당 본사 공식 매장 목록 (그룹1). run_all.py가 불러 쓴다.
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _g1 import get, clean, flat, done, imweb_list, imweb_boards, g5_array, SKIP

SOURCE = 'https://bingsudang.kr/bbs/content.php?co_id=store'


def fetch():
    a = g5_array(get(SOURCE))
    return done([(x["wr_subject"], x["wr_4"]) for x in a
                 if not re.search(r"오픈|예정|준비|폐점", (x.get("wr_6") or "") + x["wr_subject"])], 20)
