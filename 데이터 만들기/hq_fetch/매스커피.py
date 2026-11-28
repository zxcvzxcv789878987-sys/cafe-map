# 매스커피 본사 공식 매장 목록 받기 (run_all.py가 부른다)
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _hq import *

SOURCE = 'https://mass-coffee.com/store'


def fetch():
    d = jsvar(get(SOURCE), 'var DATA')
    return clean((x['name'], x['addr']) for x in d['domestic'])
