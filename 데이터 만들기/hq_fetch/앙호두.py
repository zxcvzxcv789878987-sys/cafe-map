# 앙호두 본사 공식 매장 목록 받기 (run_all.py가 부른다)
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _hq import *

SOURCE = 'https://www.anghodu.com/'


def fetch():
    h = get(SOURCE)
    return clean(re.findall(r'data-name="([^"]*)"\s*data-address="([^"]*)"', h))
