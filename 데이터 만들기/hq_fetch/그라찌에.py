# 그라찌에 본사 매장 목록 받기. run_all.py가 불러 쓴다(csv는 run_all.py가 쓴다).
import os, re, importlib.util
_s = importlib.util.spec_from_file_location('_hq_common', os.path.join(os.path.dirname(os.path.abspath(__file__)), '_common.py'))
C = importlib.util.module_from_spec(_s); _s.loader.exec_module(C)

SOURCE = 'https://www.grazie.co.kr/OURSTORES'


def fetch():
    s = C.get(SOURCE)
    i = s.find('const STORES')
    seg = s[i:s.find('];', i)]
    return C.need(re.findall(r"name:\s*'(.*?)',\s*addr:\s*'(.*?)'", seg), 20, '그라찌에')
