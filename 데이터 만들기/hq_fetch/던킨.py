# 던킨 본사 매장 목록 받기. run_all.py가 불러 쓴다(csv는 run_all.py가 쓴다).
import os, re, importlib.util
_s = importlib.util.spec_from_file_location('_hq_common', os.path.join(os.path.dirname(os.path.abspath(__file__)), '_common.py'))
C = importlib.util.module_from_spec(_s); _s.loader.exec_module(C)

SOURCE = 'https://www.dunkindonuts.co.kr/store'


def fetch():
    # 본사 지도는 가까운 매장만 준다. 전국을 0.3도 칸으로 나눠 묻는다.
    H = {'Referer': 'https://www.dunkindonuts.co.kr/store'}
    res = {}
    for y, x in C.grid_points(0.3):
        for z in C.get('https://www.dunkindonuts.co.kr/api/clientStore?x=%s&y=%s' % (x, y), headers=H, js=True)['data']:
            if z.get('SAP_S_CLOSEDATE') or z.get('VIEW_YN') == 'N':
                continue
            a = ' '.join(str(z.get(k) or '') for k in ['ADDR_SI', 'ADDR_GUGUN', 'ADDR_DETAIL']).strip() or z.get('SAP_S_SAP_ADDR')
            res[z['STORECODE']] = (z['SAP_S_NAME'], a)
    return C.need(list(res.values()), 300, '던킨')
