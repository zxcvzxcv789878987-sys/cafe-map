# 아토커피 본사 공식 매장 목록 받기 (run_all.py가 부른다)
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _hq import *

SOURCE = 'https://www.attocoffee.kr/theme/planmaker/store.php'


def fetch():
    d = jsvar(get(SOURCE), 'const STORES')
    return clean((x['st_name'], x['st_addr']) for x in d if x.get('st_addr'))
