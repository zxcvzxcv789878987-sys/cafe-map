# 디저트39 본사 공식 매장 목록 받기 (run_all.py가 부른다)
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _hq import *

SOURCE = 'https://www.dessert39.com/html/pages/store.php'


def fetch():
    h = get(SOURCE)
    return clean(re.findall(r'class="fw700 tit">(.*?)</h4>.*?<h5 class="left">주소</h5>\s*<p class="fw300 right">(.*?)</p>', h, re.S))
