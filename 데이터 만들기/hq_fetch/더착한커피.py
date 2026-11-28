# 더착한커피 본사 공식 매장 목록 받기 (run_all.py가 부른다)
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _hq import *

SOURCE = 'https://xn--9m1by48b62bvxjse.com/매장안내/'


def fetch():
    d = get_json('https://xn--9m1by48b62bvxjse.com/wp-admin/admin-ajax.php?action=store_search'
                 '&lat=36.5&lng=127.8&max_results=1000&search_radius=1000&autoload=1')
    return clean((x['store'], (x.get('address', '') + ' ' + x.get('address2', '')).strip()) for x in d)
