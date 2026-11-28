# 꿀스커피 본사 공식 매장 목록 (그룹1). run_all.py가 불러 쓴다.
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _g1 import get, clean, flat, done, imweb_list, imweb_boards, g5_array, SKIP

SOURCE = 'http://www.ggulscoffee.com/branches'


def fetch():
    sido = "서울특별시|경기도|인천광역시|강원도|강원특별자치도|충청북도|충청남도|대전광역시|세종특별자치시|광주광역시|전라북도|전북특별자치도|전라남도|경상북도|경상남도|대구광역시|부산광역시|울산광역시|제주특별자치도"
    rows = []
    for p in range(1, 30):
        x = flat(get(SOURCE + "?page=%d" % p))
        s = x[x.find("상세보기|"):]
        new = [i for i in re.findall(r"\|(?:" + sido + r")\|([^|]+)\|([^|]+)\|[^|]*\|자세히보기", "|" + s) if i not in rows]
        if not new:
            break
        rows += new
    return done(rows, 15)
