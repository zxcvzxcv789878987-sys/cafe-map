# 카페봄봄 본사 공식 매장 목록 (그룹1). run_all.py가 불러 쓴다.
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _g1 import get, clean, flat, done, imweb_list, imweb_boards, g5_array, SKIP

SOURCE = 'https://cafebombom.co.kr/theme/nero/subpage/brand/store_01.php'


def fetch():
    d = json.loads(get("https://cafebombom.co.kr/theme/nero/subpage/brand/store_map_data.php", data="",
                       headers={"Referer": SOURCE}))
    rows = [(s["store_name"], (s["store_address"] or "") + (" " + s["store_address_detail"] if s.get("store_address_detail") else ""))
            for s in d["stores"]]
    return done(rows, 200)
