# 데이롱카페 본사 공식 매장 목록 받기 (run_all.py가 부른다)
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _hq import *

SOURCE = 'https://daylong24.com/25'


def fetch():
    return clean(imweb('https://daylong24.com', '/25'))
