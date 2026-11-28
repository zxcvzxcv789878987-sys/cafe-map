# 스타벅스 본사 매장 목록 받기. run_all.py가 불러 쓴다(csv는 run_all.py가 쓴다).
import os, re, importlib.util
_s = importlib.util.spec_from_file_location('_hq_common', os.path.join(os.path.dirname(os.path.abspath(__file__)), '_common.py'))
C = importlib.util.module_from_spec(_s); _s.loader.exec_module(C)

SOURCE = 'https://www.starbucks.co.kr/store/store_map.do'


def fetch():
    H = {'X-Requested-With': 'XMLHttpRequest', 'Referer': 'https://www.starbucks.co.kr/store/store_map.do'}
    rows = []
    for sido in ['%02d' % i for i in range(1, 18)]:
        d = {'in_biz_cds': '0', 'in_scodes': '0', 'search_text': '', 'p_sido_cd': sido, 'p_gugun_cd': '',
             'isError': 'true', 'in_distance': '0', 'in_biz_cd': '', 'iend': '2000', 'searchType': 'C',
             'set_date': '', 'all_store': '0', 'whcroad_yn': '0', 'new_bool': '0'}
        j = C.get('https://www.starbucks.co.kr/store/getStore.do?r=X', data=d, headers=H, js=True)
        for s in j.get('list') or []:
            rows.append((s.get('s_name'), s.get('doro_address') or s.get('addr')))
    return C.need(rows, 1000, '스타벅스')
