# 커피마마 본사 공식 매장 목록 받기 (run_all.py가 부른다)
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _hq import *

SOURCE = 'https://www.coffeemama.co.kr/?c=3/33'


def fetch():
    return clean(pages(lambda p: 'https://www.coffeemama.co.kr/?c=3/33&sort=d_regis&orderby=desc&p=%d' % p,
                       r'class="b">(.*?)</a>\s*</td>\s*<td\s+class="addr">(.*?)</td>'))
