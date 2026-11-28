# 와플대학 본사 공식 매장 목록 받기 (run_all.py가 부른다)
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _hq import *

SOURCE = 'https://www.waffleuniv.com/child/sub/store/search/'


def fetch():
    d = get_json('https://www.waffleuniv.com/child/shop/proc/ajaxFullList.php', headers={'Referer': SOURCE})
    return clean((x['title'], ' '.join(filter(None, [x.get('sido'), x.get('gugun'), x.get('addr')]))) for x in d)
