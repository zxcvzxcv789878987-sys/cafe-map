# 사실빙 본사 공식 매장 목록 받기 (run_all.py가 부른다)
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _hq import *

SOURCE = 'https://sasilbing.com/'


def fetch():
    h = get(SOURCE)
    return clean(re.findall(r'mid_map_search_item_title">(.*?)</p>\s*<p class="mid_map_search_item_addres">(.*?)</p>', h, re.S))
