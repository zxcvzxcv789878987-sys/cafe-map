# 지유명차 본사 매장 목록 받기. run_all.py가 불러 쓴다(csv는 run_all.py가 쓴다).
import os, re, importlib.util
_s = importlib.util.spec_from_file_location('_hq_common', os.path.join(os.path.dirname(os.path.abspath(__file__)), '_common.py'))
C = importlib.util.module_from_spec(_s); _s.loader.exec_module(C)

SOURCE = 'http://www.gutea.co.kr/ab-1072'


def fetch():
    def parse(s):
        r = re.findall(r'class="onlyPC".*?l_name="\d+"[^>]*>(.*?)</span></span><span[^>]*>(.*?)</span>', s, re.S)
        return [(n, a) for n, a in r if '오픈 예정' not in n and '오픈예정' not in n]
    rows = C.pages(lambda p: 'http://www.gutea.co.kr/ab-1072?PB_1467090967=%d' % p, parse, 60)
    return C.need([(re.sub(r'\(.*?오픈\)', '', n).strip(), a) for n, a in rows], 30, '지유명차')
