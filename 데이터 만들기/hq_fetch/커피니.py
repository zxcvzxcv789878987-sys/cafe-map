# 커피니 본사 공식 매장 목록 (그룹1). run_all.py가 불러 쓴다.
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _g1 import get, clean, flat, done, imweb_list, imweb_boards, g5_array, SKIP

SOURCE = 'https://www.coffeenie.co.kr/techboard/bbs/board.php?bo_table=stores'


def fetch():
    rows = {}
    for p in range(1, 60):
        t = get(SOURCE + "&page=%d" % p)
        items = re.findall(r'<td align="center" valign="middle">([^<]*)</td>\s*<td align="left" valign="middle">\s*'
                           r'<div class="text_title" style="width:283px[^>]*>\s*<a href="[^"]*wr_id=(\d+)[^"]*">(.*?)</a>', t, re.S)
        new = [i for i in items if i[1] not in rows]
        if not new:
            break
        for n, i, a in new:
            rows[i] = (n, a)
    return done(list(rows.values()), 50)
