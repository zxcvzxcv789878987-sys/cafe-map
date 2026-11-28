# 메가MGC커피 본사 공식 매장 목록 (그룹1). run_all.py가 불러 쓴다.
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _g1 import get, clean, flat, done, imweb_list, imweb_boards, g5_array, SKIP

SOURCE = 'https://www.mega-mgccoffee.com/store/find/'


def fetch():
    t = get("https://www.mega-mgccoffee.com/store/find/store_search.php?store_search=%20",
            headers={"Referer": SOURCE})
    rows = re.findall(r'<b>(.*?)</b>\s*</div>\s*<div class="cont_text_inner cont_text_info">\s*(.*?)\s{2,}', t, re.S)
    return done(rows, 1000)
