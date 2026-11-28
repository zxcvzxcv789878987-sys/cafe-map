# 라떼킹 본사 공식 매장 목록 받기 (run_all.py가 부른다)
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _hq import *

SOURCE = 'https://www.latteking.co.kr/STORE'


def fetch():
    return clean(imweb('https://www.latteking.co.kr', '/STORE'))
