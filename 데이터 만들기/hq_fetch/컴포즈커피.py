# 컴포즈커피 본사 공식 매장 목록 받기 (run_all.py가 부른다)
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _hq import *

SOURCE = 'https://composecoffee.com/findstore'


def fetch():
    h = get(SOURCE)
    d = jsvar(h, 'var markerData')
    return clean((x[4], x[5]) for x in d)
