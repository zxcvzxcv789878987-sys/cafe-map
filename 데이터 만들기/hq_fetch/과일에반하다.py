# 과일에반하다 본사 매장 목록 받기. run_all.py가 불러 쓴다(csv는 run_all.py가 쓴다).
import os, re, importlib.util
_s = importlib.util.spec_from_file_location('_hq_common', os.path.join(os.path.dirname(os.path.abspath(__file__)), '_common.py'))
C = importlib.util.module_from_spec(_s); _s.loader.exec_module(C)

SOURCE = 'https://www.fruta.co.kr/store'


def fetch():
    return C.need(C.imweb_map('https://www.fruta.co.kr/store'), 20, '과일에반하다')
