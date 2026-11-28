# 백미당 본사 공식 매장 목록 (그룹1). run_all.py가 불러 쓴다.
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _g1 import get, clean, flat, done, imweb_list, imweb_boards, g5_array, SKIP

SOURCE = 'https://www.baekmidang.co.kr/home/shop/list'


def fetch():
    t = get("https://www.baekmidang.co.kr/home/shop/ajaxList?searchShopNm=", headers={"Referer": SOURCE})
    rows = re.findall(r'<li>\s*<div>(.*?)</div>\s*<div>\s*<ul>\s*<li>\s*<p>주소</p>\s*<p>(.*?)(?:<a |</p>)', t, re.S)
    return done(rows, 30)
