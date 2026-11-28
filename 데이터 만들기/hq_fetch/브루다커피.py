# 브루다커피 본사 공식 매장 목록 받기 (run_all.py가 부른다)
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _hq import *

SOURCE = 'https://www.brewdacoffee.com/store'


def fetch():
    return clean(imweb('https://www.brewdacoffee.com', '/store', prefix='브루다커피 '))
