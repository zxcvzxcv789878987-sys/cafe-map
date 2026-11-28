# 시나본 본사 매장 목록 받기. run_all.py가 불러 쓴다(csv는 run_all.py가 쓴다).
import os, re, importlib.util
_s = importlib.util.spec_from_file_location('_hq_common', os.path.join(os.path.dirname(os.path.abspath(__file__)), '_common.py'))
C = importlib.util.module_from_spec(_s); _s.loader.exec_module(C)

SOURCE = 'https://www.cinnabon.kr/STORE'


def fetch():
    # 페이지 안의 구조화 자료(JSON-LD)에서 매장 이름과 주소를 읽는다.
    s = C.get(SOURCE)
    r = re.findall(r'"name":"([^"]+)","url":"https://www\.cinnabon\.kr/STORE/[^"]+"[^{}]*?"address":\{"@type":"PostalAddress","streetAddress":"([^"]+)"', s)
    return C.need(r, 6, '시나본')
