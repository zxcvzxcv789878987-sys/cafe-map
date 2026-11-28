# 봉명동내커피 본사 매장 목록 받기. run_all.py가 불러 쓴다(csv는 run_all.py가 쓴다).
import os, re, importlib.util
_s = importlib.util.spec_from_file_location('_hq_common', os.path.join(os.path.dirname(os.path.abspath(__file__)), '_common.py'))
C = importlib.util.module_from_spec(_s); _s.loader.exec_module(C)

SOURCE = 'https://www.xn--220bq3dn1huxcd07aowi.com/'


def fetch():
    j = C.get('https://www.xn--220bq3dn1huxcd07aowi.com/api/store.php', headers={'Referer': SOURCE}, js=True)['data']
    return C.need([(x['name'], (x['address1'] or '') + ' ' + (x['address2'] or '')) for x in j], 60, '봉명동내커피')
