# 카페16온스 본사 공식 매장 목록 받기 (run_all.py가 부른다)
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _hq import *

SOURCE = 'https://www.cafe16oz.com/bbs/branch.php'


def fetch():
    d = get_json('https://www.cafe16oz.com/bbs/get_branch_list.php')
    return clean((x['name'], x['address']) for x in d['stores'])
