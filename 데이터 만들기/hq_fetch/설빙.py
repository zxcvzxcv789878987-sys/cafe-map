# 설빙 본사 공식 매장 목록 (그룹1). run_all.py가 불러 쓴다.
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _g1 import get, clean, flat, done, imweb_list, imweb_boards, g5_array, SKIP

SOURCE = 'https://sulbing.com/store/'


def fetch():
    import urllib.parse
    rows = []
    for a in "서울특별시 경기도 인천광역시 대전광역시 대구광역시 울산광역시 전라남도 전라북도 충청남도 충청북도 제주특별자치도 세종특별자치시 광주광역시 부산광역시 경상북도 경상남도 강원도".split():
        t = get(SOURCE + "?addr1=" + urllib.parse.quote(a) + "&addr2=&search=")
        for ti, c in re.findall(r"\{ title: '(.*?)', content:'(.*?)', latlng", t, re.S):
            m = re.search(r'매장주소</strong><div class="con">(.*?)</div>', c)
            if m:
                rows.append((ti, m.group(1)))
    return done(rows, 300)
