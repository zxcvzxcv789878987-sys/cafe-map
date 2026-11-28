# 테라커피 본사 공식 매장 목록 받기 (run_all.py가 부른다)
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _hq import *

SOURCE = 'https://teracoffee.com/default/find/'


def fetch():
    return clean(pages(lambda p: 'https://teracoffee.com/default/find/index.php?com_board_id=15&com_board_page=%d' % p,
                       r"gallery_title'>(.*?)</span>.*?매장주소 : (.*?)</font>"))
