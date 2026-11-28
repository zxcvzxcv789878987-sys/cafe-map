# 아덴블랑제리 본사 공식 매장 목록 받기 (run_all.py가 부른다)
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _hq import *

SOURCE = 'http://aden-cafe.com/bbs/board.php?bo_table=free'


def fetch():
    ids = []
    for p in range(1, 20):
        h = get(SOURCE + '&page=%d' % p)
        new = [i for i in re.findall(r'bo_table=free&amp;wr_id=(\d+)', h) if i not in ids]
        if not new:
            break
        ids += new
    rows = []
    for i in ids:
        h = get(SOURCE + '&wr_id=' + i)
        t = re.search(r'<title>(.*?)</title>', h, re.S)
        m = re.search(r'주소\s*:\s*([^<\n]+)', h)
        title = txt(t.group(1)).replace(' > STORE | ADEN', '') if t else ''
        if '아덴' in title and m:
            rows.append((title, m.group(1)))
    return clean(rows)
