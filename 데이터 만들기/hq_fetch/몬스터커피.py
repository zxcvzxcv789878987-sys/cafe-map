# 몬스터커피 본사 매장 목록 받기. run_all.py가 불러 쓴다(csv는 run_all.py가 쓴다).
import os, re, importlib.util
_s = importlib.util.spec_from_file_location('_hq_common', os.path.join(os.path.dirname(os.path.abspath(__file__)), '_common.py'))
C = importlib.util.module_from_spec(_s); _s.loader.exec_module(C)

SOURCE = 'https://www.monster-coffee.com/store/store'


def fetch():
    s = C.get(SOURCE)
    m = re.search(r"csrf_hash = '(\w+)'", s)
    n = re.search(r"csrf_name = '(\w+)'", s)
    j = C.get('https://www.monster-coffee.com/api/store/get_store_list', data={n.group(1): m.group(1)},
              headers={'X-Requested-With': 'XMLHttpRequest', 'Referer': SOURCE}, js=True)
    return C.need([(x['s_name'], x['s_address']) for x in j], 50, '몬스터커피')
