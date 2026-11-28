# 아임일리터 본사 매장 목록 받기. run_all.py가 불러 쓴다(csv는 run_all.py가 쓴다).
import os, re, importlib.util
_s = importlib.util.spec_from_file_location('_hq_common', os.path.join(os.path.dirname(os.path.abspath(__file__)), '_common.py'))
C = importlib.util.module_from_spec(_s); _s.loader.exec_module(C)

SOURCE = 'https://www.im1l.co.kr/brand/stores'


def fetch():
    # 본사 자료에 출처 표시가 있어 "공식"이 들어간 매장만 쓴다.
    j = C.get('https://www.im1l.co.kr/api/catalog?type=store', headers={'Referer': SOURCE}, js=True)['items']
    return C.need([(x['payload']['name'], x['payload']['address']) for x in j
                   if '공식' in (x['payload'].get('sourceStatus') or '') and x.get('status') == 'published'], 30, '아임일리터')
