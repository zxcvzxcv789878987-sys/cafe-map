# 엔제리너스 본사 매장 목록 받기. run_all.py가 불러 쓴다(csv는 run_all.py가 쓴다).
import os, re, importlib.util
_s = importlib.util.spec_from_file_location('_hq_common', os.path.join(os.path.dirname(os.path.abspath(__file__)), '_common.py'))
C = importlib.util.module_from_spec(_s); _s.loader.exec_module(C)

SOURCE = 'https://www.lotteeatz.com/searchStore'


def fetch():
    H = {'Referer': 'https://www.lotteeatz.com/searchStore'}
    rows = []
    for sd in [x['sidoCode'] for x in C.get('https://www.lotteeatz.com/api/v1/region', headers=H, js=True)]:
        for p in range(1, 30):
            j = C.get('https://www.lotteeatz.com/api/v1/stores/search?sidoCode=%s&brandList=20&page=%d&size=100' % (sd, p), headers=H, js=True)
            c = j.get('content') or []
            for s in c:
                n = (s.get('storeNm') or '').strip()
                # 1002는 시험 매장, 2016은 스탠브루(다른 브랜드), 빌라드샬롯도 다른 브랜드
                if s.get('spotCode') in ('1002', '2016') or not n or n.startswith('빌라드샬롯') or '테스트' in n:
                    continue
                a = s.get('adres') or {}
                rows.append((n, (str(a.get('adres') or '') + ' ' + str(a.get('detailAdres') or '')).strip()))
            if len(c) < 100:
                break
    return C.need(rows, 100, '엔제리너스')
