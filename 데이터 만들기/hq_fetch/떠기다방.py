# 떠기다방 본사 공식 매장 목록 받기 (run_all.py가 부른다)
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _hq import *

SOURCE = 'https://tteogi-coffee.com/'


def fetch():
    return clean(imweb('https://tteogi-coffee.com', '/', prefix='떠기다방 '))
