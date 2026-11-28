# 커피홀베이커리 본사 공식 매장 목록 받기 (run_all.py가 부른다)
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _hq import *

SOURCE = 'https://www.coffeehole.co.kr/sub04/sub01.php'


def fetch():
    d = jsvar(get(SOURCE), 'const mapInfo')
    return clean((x['name'], x['address']) for x in d if '예정' not in (x.get('status') or ''))
