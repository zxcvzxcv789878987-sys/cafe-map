# 카페마일로 본사 매장 목록 받기. run_all.py가 불러 쓴다(csv는 run_all.py가 쓴다).
import os, re, importlib.util
_s = importlib.util.spec_from_file_location('_hq_common', os.path.join(os.path.dirname(os.path.abspath(__file__)), '_common.py'))
C = importlib.util.module_from_spec(_s); _s.loader.exec_module(C)

SOURCE = 'https://www.cafemilo.co.kr/map/'


def fetch():
    H = {'X-Requested-With': 'XMLHttpRequest', 'Referer': SOURCE}
    rows = []
    for p in range(1, 40):
        j = C.get('https://www.cafemilo.co.kr/map/ajax.map_kakao.php?mode=all&page=%d' % p, headers=H, js=True)
        rows += [(x['office_name'], x['address']) for x in j['rows']]
        if not j.get('hasNextPage'):
            break
    return C.need(rows, 30, '카페마일로')
