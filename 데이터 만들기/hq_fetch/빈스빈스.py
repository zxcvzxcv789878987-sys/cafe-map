# 빈스빈스 본사 공식 매장 목록 받기 (run_all.py가 부른다)
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _hq import *

SOURCE = 'http://www.beansbins.com/?STC=01&act=store.store_list'


def fetch():
    return clean(pages(lambda p: 'http://www.beansbins.com/?STC=01&act=store.store_list&page=%d' % p,
                       r'<tr class="store-item">\s*<td>(.*?)</td>\s*<td>(.*?)</td>'))
