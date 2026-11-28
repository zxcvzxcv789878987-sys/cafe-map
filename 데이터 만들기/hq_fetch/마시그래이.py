# 마시그래이 본사 공식 매장 목록 (그룹1). run_all.py가 불러 쓴다.
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _g1 import get, clean, flat, done, imweb_list, imweb_boards, g5_array, SKIP

SOURCE = 'https://www.masigray.com:5021/Store/storeList.asp'


def fetch():
    rows = {}
    for p in range(1, 40):
        t = get(SOURCE + "?page=%d&s_type=st_name&s_cate=&idx=&s_value=" % p)
        items = re.findall(r'onclick="view\((\d+)\)" target="_blank">\s*<div class="store">(.*?)</div>\s*<div class="add">(.*?)</div>', t, re.S)
        items += re.findall(r'onclick="view\((\d+)\)">\s*<div class="item">.*?<strong>(.*?)</strong>\s*<p><em>주소</em>(.*?)</p>', t, re.S)
        new = [i for i in items if i[0] not in rows]
        if not new:
            break
        for i, n, a in new:
            rows[i] = (n, a)
    return done(list(rows.values()), 30)
