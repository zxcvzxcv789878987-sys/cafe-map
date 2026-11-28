# 커피인류 본사 공식 매장 목록 받기 (run_all.py가 부른다)
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _hq import *

SOURCE = 'https://www.coffeeinryu.com/'


def fetch():
    h = get('https://www.coffeeinryu.com/ajax/ajax.store.php', b'',
            {'X-Requested-With': 'XMLHttpRequest', 'Referer': SOURCE, 'Origin': 'https://www.coffeeinryu.com'})
    return clean(re.findall(r'<strong>(.*?)</strong>\s*<p>(.*?)</p>', h, re.S))
