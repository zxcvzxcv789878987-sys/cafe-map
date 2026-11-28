# 히스피 본사 매장 목록 받기. run_all.py가 불러 쓴다(csv는 run_all.py가 쓴다).
import os, re, importlib.util
_s = importlib.util.spec_from_file_location('_hq_common', os.path.join(os.path.dirname(os.path.abspath(__file__)), '_common.py'))
C = importlib.util.module_from_spec(_s); _s.loader.exec_module(C)

SOURCE = 'https://hisffee.com/store'


def fetch():
    r = C.imweb_card('https://hisffee.com/store')
    return C.need([x for x in r if not re.search(r'준비|예정', x[1])], 20, '히스피')
