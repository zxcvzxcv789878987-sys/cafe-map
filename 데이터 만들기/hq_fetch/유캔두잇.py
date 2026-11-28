# 유캔두잇 본사 공식 매장 목록 받기 (run_all.py가 부른다)
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _hq import *

SOURCE = 'https://ucandoeat.com/sub/sub06_02.php'


def fetch():
    return clean(pages(lambda p: 'https://ucandoeat.com/sub/sub06_02.php?boardid=store&offset=%d' % ((p - 1) * 10),
                       r'<td>([^<]*)</td>\s*<td class="subject">(.*?)</td>'))
