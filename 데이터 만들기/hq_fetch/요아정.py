# 요아정 본사 공식 매장 목록 받기 (run_all.py가 부른다)
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _hq import *

SOURCE = 'https://www.yoajung.co.kr/bbs/content.php?co_id=menustore'


def fetch():
    h = get(SOURCE)
    return clean(re.findall(r'con17_mid_map_search_item store [^"]*">\s*<p class="con17_mid_map_search_item_title">(.*?)</p>\s*<p class="con17_mid_map_search_item_address">(.*?)</p>', h, re.S))
