# 나인블럭 본사 매장 목록 받기. run_all.py가 불러 쓴다(csv는 run_all.py가 쓴다).
import os, re, importlib.util
_s = importlib.util.spec_from_file_location('_hq_common', os.path.join(os.path.dirname(os.path.abspath(__file__)), '_common.py'))
C = importlib.util.module_from_spec(_s); _s.loader.exec_module(C)

SOURCE = 'https://www.dfdgroup.com/board/hub_store'


def fetch():
    rows = []
    for p in range(1, 6):
        s = C.get('https://www.dfdgroup.com/board/hub_store?type_sel=&fa_sel=CT03&page=%d' % p)
        rows += re.findall(r'class="brand">(.*?)</td>\s*<td class="store">(.*?)</td>\s*<td class="addr">(.*?)</td>', s[s.find('<tbody'):], re.S)
    return C.need([(n, a) for b, n, a in rows if b.strip() == '나인블럭'], 3, '나인블럭')
