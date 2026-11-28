# 이디야 본사 매장 목록 받기. run_all.py가 불러 쓴다(csv는 run_all.py가 쓴다).
import os, re, importlib.util
_s = importlib.util.spec_from_file_location('_hq_common', os.path.join(os.path.dirname(os.path.abspath(__file__)), '_common.py'))
C = importlib.util.module_from_spec(_s); _s.loader.exec_module(C)

SOURCE = 'https://www.ediya.com/contents/find_store.html'


def fetch():
    # 지역 검색은 결과가 많으면 "over"를 돌려준다. 시군구로 묻고, 넘치면 도로명으로 나눠 묻는다.
    H = {'X-Requested-With': 'XMLHttpRequest', 'Referer': 'https://www.ediya.com/contents/find_store.html'}
    res = {}
    def q(addr):
        e = C.get('https://www.ediya.com/inc/ajax_adm_map.php', data={'gubun': 'map', 'address': addr}, headers=H)
        e = e.strip()
        if e in ('over', 'none', ''):
            return e
        p = e.split('_&12345&_')
        for a, n in zip(p[0].split('///'), p[2].split('///')):
            if n.strip():
                res[(n.strip(), a.strip())] = 1
        return 'ok'
    sgg, roads = C.regions()
    short = {'서울특별시': '서울', '부산광역시': '부산', '대구광역시': '대구', '인천광역시': '인천',
             '대전광역시': '대전', '울산광역시': '울산', '전남광주통합특별시': '광주'}
    dupe = {}
    for sd, sg in sgg:
        dupe[sg] = dupe.get(sg, 0) + 1
    done = set()
    for sd, sg in sgg:
        key = (short[sd] + ' ' + sg) if dupe[sg] > 1 and sd in short else sg
        if key in done:
            continue
        done.add(key)
        if q(key) == 'over':
            for rd in roads[(sd, sg)]:
                q(sg + ' ' + rd)
    return C.need(list(res), 1000, '이디야')
