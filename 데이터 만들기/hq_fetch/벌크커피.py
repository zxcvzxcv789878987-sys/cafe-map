# 벌크커피 본사 공식 매장 목록 (그룹1). run_all.py가 불러 쓴다.
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _g1 import get, clean, flat, done, imweb_list, imweb_boards, g5_array, SKIP

SOURCE = 'https://www.bulkcoffee.co.kr/landing/#store'


def fetch():
    t = get("https://www.bulkcoffee.co.kr/landing/")
    s = t[t.find('id="store"'):]
    seen, rows = set(), []
    for iid, name in re.findall(r'data-item-id="(\d+)" data-mg-search="([^"]*)"', s):
        if iid in seen:
            continue
        seen.add(iid)
        x = clean(get("https://www.bulkcoffee.co.kr/wp-admin/admin-ajax.php",
                      data={"action": "mg_lb_contents", "pid": iid},
                      headers={"Referer": "https://www.bulkcoffee.co.kr/landing/"}))
        m = re.search(r"주\s*소\s*:\s*(.*?)\s*(전\s*화\s*:|로드뷰|$)", x)
        if m:
            rows.append((name, m.group(1)))
    return done(rows, 100)
