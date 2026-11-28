# 천씨씨커피 본사 매장 목록 받기. run_all.py가 불러 쓴다(csv는 run_all.py가 쓴다).
import os, re, importlib.util
_s = importlib.util.spec_from_file_location('_hq_common', os.path.join(os.path.dirname(os.path.abspath(__file__)), '_common.py'))
C = importlib.util.module_from_spec(_s); _s.loader.exec_module(C)

SOURCE = 'https://www.1000cccoffee.com/bbs/content.php?co_id=shop'


def fetch():
    t = C.text(SOURCE)
    t = t[t.find('검색되었습니다'):]
    return C.need(re.findall(r'(\S+점) (.*?) 전화번호', t), 50, '천씨씨커피')
