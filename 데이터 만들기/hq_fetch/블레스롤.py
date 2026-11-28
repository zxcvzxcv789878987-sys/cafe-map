# 블레스롤 본사 공식 매장 목록 (그룹1). run_all.py가 불러 쓴다.
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _g1 import get, clean, flat, done, imweb_list, imweb_boards, g5_array, SKIP

SOURCE = 'https://www.blessroll.com/24'


def fetch():
    x = flat(get(SOURCE))
    s = x[x.find("전남·광주|경기·인천|"):x.find("해당 지역에 매장이 없습니다")]
    rows = re.findall(r"\|(?:대전|충북|충남|전북|전남|광주|경기|인천|서울|부산|대구|울산|세종|강원|경북|경남|제주)\|([^|]+)\|([^|]+)\|길찾기", s)
    return done(rows, 5)
