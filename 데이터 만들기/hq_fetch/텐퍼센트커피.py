# 텐퍼센트커피 본사 공식 매장 목록 받기 (run_all.py가 부른다)
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _hq import *

SOURCE = 'https://www.tenpercentcoffee.com/sub/sub41.php'


def fetch():
    h = get(SOURCE)
    return clean(re.findall(r'class="rlwbp idfont1">(.*?)</p>\s*<p class="rlwsp">(.*?)</p>', h, re.S))
