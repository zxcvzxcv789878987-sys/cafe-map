# 커피스토어 본사 매장 목록 받기. run_all.py가 불러 쓴다(csv는 run_all.py가 쓴다).
import os, re, importlib.util
_s = importlib.util.spec_from_file_location('_hq_common', os.path.join(os.path.dirname(os.path.abspath(__file__)), '_common.py'))
C = importlib.util.module_from_spec(_s); _s.loader.exec_module(C)

SOURCE = 'https://xn--9t4b29ctzlbyc75f.com'


def fetch():
    s = C.get(SOURCE)
    r = re.findall(r'class="mid_map_search_item_title">(.*?)</p>\s*<p class="mid_map_search_item_addres">(.*?)</p>', s, re.S)
    return C.need([(n, a) for n, a in r if C.clean(n) != '매장명'], 8, '커피스토어')
