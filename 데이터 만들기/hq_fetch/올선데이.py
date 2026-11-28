# 올선데이 본사 매장 목록 받기. run_all.py가 불러 쓴다(csv는 run_all.py가 쓴다).
import os, re, importlib.util
_s = importlib.util.spec_from_file_location('_hq_common', os.path.join(os.path.dirname(os.path.abspath(__file__)), '_common.py'))
C = importlib.util.module_from_spec(_s); _s.loader.exec_module(C)

SOURCE = 'http://allsunday.co.kr/sub04/sub04_01.php'


def fetch():
    j = C.get('http://allsunday.co.kr/store_ajax.php', data={'act': 'all'},
              headers={'X-Requested-With': 'XMLHttpRequest', 'Referer': SOURCE}, js=True)
    rows = [(x['storeName'], ' '.join(str(x.get(k) or '') for k in ('storeAddr1', 'storeAddr2', 'storeAddr3')))
            for x in j['result'] if str(x.get('storeVisible', '1')) == '1']
    return C.need(rows, 6, '올선데이')
