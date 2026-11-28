# 파리바게뜨 본사 매장 목록 받기. run_all.py가 불러 쓴다(csv는 run_all.py가 쓴다).
import os, re, importlib.util
_s = importlib.util.spec_from_file_location('_hq_common', os.path.join(os.path.dirname(os.path.abspath(__file__)), '_common.py'))
C = importlib.util.module_from_spec(_s); _s.loader.exec_module(C)

SOURCE = 'https://www.paris.co.kr/store/'


def fetch():
    H = {'Referer': 'https://www.paris.co.kr/store/', 'X-Requested-With': 'XMLHttpRequest'}
    A = C.json.loads(C.get('https://www.paris.co.kr/wp-admin/admin-ajax.php?action=pb_store_get_area', headers=H))
    rows = []
    for v in A.values():
        for ch in v.get('children') or []:
            q = C.urllib.parse.urlencode({'action': 'pb_store_get_list', 'type': '#area', 'keyword': '', 'area1': v['id'], 'area2': ch['id'],
                                          'is_delivery': 'false', 'is_cafe': 'false', 'is_parking': 'false', 'is_pickup': 'false',
                                          'is_catering': 'false', 'is_hybrid': 'false'})
            s = C.get('https://www.paris.co.kr/wp-admin/admin-ajax.php?' + q, headers=H, timeout=60)
            rows += re.findall(r'class="label">(.*?)</span>.*?class="store-addr">(.*?)</p>', s, re.S)
    return C.need(rows, 1500, '파리바게뜨')
