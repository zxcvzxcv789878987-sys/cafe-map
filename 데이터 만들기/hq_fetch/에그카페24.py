# 에그카페24 본사 매장 목록 받기. run_all.py가 불러 쓴다(csv는 run_all.py가 쓴다).
import os, re, importlib.util
_s = importlib.util.spec_from_file_location('_hq_common', os.path.join(os.path.dirname(os.path.abspath(__file__)), '_common.py'))
C = importlib.util.module_from_spec(_s); _s.loader.exec_module(C)

SOURCE = 'https://www.lsco.co.kr/bbs/board.php?bo_table=map'


def fetch():
    def parse(s):
        return [(n, a.replace('&nbsp;0', '')) for n, a in
                re.findall(r'class="td_date">(.*?)</td>.*?class="td_44 hide_mo"><a[^>]*>(.*?)</a>', s, re.S)]
    return C.need(C.pages(lambda p: SOURCE + '&page=%d' % p, parse, 100), 200, '에그카페24')
