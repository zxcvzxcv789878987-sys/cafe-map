# 쿼드커피 본사 매장 목록 받기. run_all.py가 불러 쓴다(csv는 run_all.py가 쓴다).
import os, re, importlib.util
_s = importlib.util.spec_from_file_location('_hq_common', os.path.join(os.path.dirname(os.path.abspath(__file__)), '_common.py'))
C = importlib.util.module_from_spec(_s); _s.loader.exec_module(C)

SOURCE = 'https://www.quadcoffee.co.kr/franchise/list2'


def fetch():
    def parse(s):
        s = s[s.find('전국매장'):]
        return re.findall(r'class="name">(.*?)</span>\s*<div class="info_list">\s*<span class="add">(.*?)</span>', s, re.S)
    return C.need(C.pages(lambda p: SOURCE + '?page=%d' % p, parse, 60), 20, '쿼드커피')
