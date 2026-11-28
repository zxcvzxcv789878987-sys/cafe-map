# 폴바셋 본사 공식 매장 목록 (그룹1). run_all.py가 불러 쓴다.
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _g1 import get, clean, flat, done, imweb_list, imweb_boards, g5_array, SKIP

SOURCE = 'https://www.baristapaulbassett.co.kr/store/Store.pb'


def fetch():
    d = json.loads(get("https://www.baristapaulbassett.co.kr/store/getStoreList.pb",
                       data="searchType=storeName&surDistance=&myLocLati=37.5&myLocLongi=127&areaCd=&cityCd=&listSort=D&shopName=",
                       headers={"Referer": SOURCE}))
    return done([(x["shopName"], x["address"]) for x in d], 80)
