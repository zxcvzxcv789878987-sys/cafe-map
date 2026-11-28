# 파머스빈 본사 공식 매장 목록 받기 (run_all.py가 부른다)
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _hq import *

SOURCE = 'http://farmersbean.kr/layout/res/home.php?go=store.list&mid=40'


def fetch():
    rows = pages(lambda p: SOURCE + '&start=%d' % ((p - 1) * 10),
                 r'<td>\d+</td>\s*<td>[^<]*</td>\s*<td>([^<]*)</td>\s*<td class=.left dis_none.>([^<]*)</td>')
    return clean((n, re.sub(r'^\(\d{5}\)\s*', '', a)) for n, a in rows)
