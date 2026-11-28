# 어벤더치 본사 공식 매장 목록 받기 (run_all.py가 부른다)
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _hq import *

SOURCE = 'http://www.avendutch.com/store/store.php'


def fetch():
    return clean(pages(lambda p: 'http://www.avendutch.com/store/store.php?addr1=&addr2=&searchName=&pg=%d' % p,
                       r'<div class="name">\s*<span>(.*?)</span>.*?<span class="address">(.*?)</span>'))
