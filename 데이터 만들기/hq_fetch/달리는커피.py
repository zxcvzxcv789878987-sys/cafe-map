# 달리는커피 본사 매장 목록 받기. run_all.py가 불러 쓴다(csv는 run_all.py가 쓴다).
import os, re, importlib.util
_s = importlib.util.spec_from_file_location('_hq_common', os.path.join(os.path.dirname(os.path.abspath(__file__)), '_common.py'))
C = importlib.util.module_from_spec(_s); _s.loader.exec_module(C)

SOURCE = 'https://dalcu.co.kr/bbs/content.php?co_id=store'


def fetch():
    t = C.text('https://dalcu.co.kr/bbs/content.php?co_id=store')
    t = t[t.find('지역별 매장 안내'):t.find('매장명 주소 영업시간 문의전화')]
    return C.need(re.findall(r'(\S+) 주소 (.*?) 영업시간', t), 80, '달리는커피')
