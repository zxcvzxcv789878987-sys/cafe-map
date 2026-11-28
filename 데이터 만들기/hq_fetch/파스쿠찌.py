# 파스쿠찌 본사 매장 목록 받기. run_all.py가 불러 쓴다(csv는 run_all.py가 쓴다).
import os, re, importlib.util
_s = importlib.util.spec_from_file_location('_hq_common', os.path.join(os.path.dirname(os.path.abspath(__file__)), '_common.py'))
C = importlib.util.module_from_spec(_s); _s.loader.exec_module(C)

SOURCE = 'https://www.pascucci.co.kr/store/storeList.asp'


def fetch():
    rows, seen = [], set()
    for p in range(1, 120):
        s = C.get('https://www.pascucci.co.kr/store/storeList.asp?page=%d' % p)
        r = re.findall(r'class="storeName">\s*<strong>(.*?)</strong>.*?class="addr">(.*?)</p>', s, re.S)
        new = [x for x in r if x not in seen]
        if not new:
            break
        seen |= set(new)
        rows += new
    return C.need([(n, a) for n, a in rows if '휴점' not in n], 200, '파스쿠찌')
