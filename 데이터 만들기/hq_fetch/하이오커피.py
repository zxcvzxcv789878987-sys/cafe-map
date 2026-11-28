# 하이오커피 본사 공식 매장 목록 받기 (run_all.py가 부른다)
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _hq import *

SOURCE = 'https://www.hiocoffee.com/sub/store/list.html'


def fetch():
    h = get(SOURCE)
    return clean(re.findall(r'<strong>([^<]*)</strong>\s*<p>([^<]*)<br', h))
