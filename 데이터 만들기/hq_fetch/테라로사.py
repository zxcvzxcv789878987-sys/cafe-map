# 테라로사 본사 공식 매장 목록 받기 (run_all.py가 부른다)
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _hq import *

SOURCE = 'https://www.terarosa.com/store/'


def fetch():
    d = get_json('https://www.terarosa.com/api/store/list/', headers={'X-Requested-With': 'XMLHttpRequest', 'Referer': SOURCE})
    return clean((x['StoreName'], (x.get('Address1') or '') + ' ' + (x.get('Address2') or '')) for x in d['stores'])
