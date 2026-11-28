# 크로앙쥬 본사 공식 매장 목록 받기 (run_all.py가 부른다)
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _hq import *

SOURCE = 'https://croiange.com/?page_id=1561'


def fetch():
    L = lines(get(SOURCE))
    return clean(tuple(s.strip() for s in x.split('│', 1)) for x in L if '│' in x and 'USA' not in x)
