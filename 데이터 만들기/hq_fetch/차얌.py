# 차얌 본사 매장 목록 받기. run_all.py가 불러 쓴다(csv는 run_all.py가 쓴다).
import os, re, importlib.util
_s = importlib.util.spec_from_file_location('_hq_common', os.path.join(os.path.dirname(os.path.abspath(__file__)), '_common.py'))
C = importlib.util.module_from_spec(_s); _s.loader.exec_module(C)

SOURCE = 'http://www.chayam.co.kr/contents/store_find.html'


def fetch():
    rows = C.pages(lambda p: SOURCE + '?page=%d' % p, lambda s: re.findall(r'<dt>(.*?)<br/><em>(.*?)</em></dt>', s, re.S), 40)
    return C.need(rows, 20, '차얌')
