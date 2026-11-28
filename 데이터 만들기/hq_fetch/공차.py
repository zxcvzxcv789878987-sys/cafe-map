# 공차 본사 매장 목록 받기. run_all.py가 불러 쓴다(csv는 run_all.py가 쓴다).
import os, re, importlib.util
_s = importlib.util.spec_from_file_location('_hq_common', os.path.join(os.path.dirname(os.path.abspath(__file__)), '_common.py'))
C = importlib.util.module_from_spec(_s); _s.loader.exec_module(C)

SOURCE = 'https://www.gong-cha.co.kr/brand/store/list'


def fetch():
    def parse(s):
        x = s[s.find('table-wrap'):]
        return re.findall(r'cell name">\s*<div>(.*?)</div>.*?cell addr">\s*<div>(.*?)</div>', x, re.S)
    rows = C.pages(lambda p: 'https://www.gong-cha.co.kr/brand/store/list?page=%d&sido=&gugun=&keyword=' % p, parse, 150)
    return C.need([(n, a) for n, a in rows if '폐점' not in n], 400, '공차')
