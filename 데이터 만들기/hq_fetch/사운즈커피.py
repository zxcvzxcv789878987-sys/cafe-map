# 사운즈커피 본사 매장 목록 받기. run_all.py가 불러 쓴다(csv는 run_all.py가 쓴다).
import os, re, importlib.util
_s = importlib.util.spec_from_file_location('_hq_common', os.path.join(os.path.dirname(os.path.abspath(__file__)), '_common.py'))
C = importlib.util.module_from_spec(_s); _s.loader.exec_module(C)

SOURCE = 'https://soundscoffee.kr/branch'


def fetch():
    s = C.get(SOURCE)
    r = re.findall(r'font-size: 16px;">([^<]{2,40}?)</span>.{0,300}?&middot;\s*([^<&]+?)\s*(?:<br>|</span>)', s, re.S)
    return C.need([(n, a) for n, a in r if '전화' not in a], 20, '사운즈커피')
