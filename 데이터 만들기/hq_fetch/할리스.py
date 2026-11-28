# 할리스 본사 매장 목록 받기. run_all.py가 불러 쓴다(csv는 run_all.py가 쓴다).
import os, re, importlib.util
_s = importlib.util.spec_from_file_location('_hq_common', os.path.join(os.path.dirname(os.path.abspath(__file__)), '_common.py'))
C = importlib.util.module_from_spec(_s); _s.loader.exec_module(C)

SOURCE = 'https://www.hollys.co.kr/store/korea/korStore2.do'


def fetch():
    rows, prev = [], None
    for p in range(1, 150):
        s = C.get('https://www.hollys.co.kr/store/korea/korStore2.do?pageNo=%d' % p)
        x = s[s.find('<tbody'):s.find('</tbody>')]
        r = re.findall(r"storeView\(\d+\); return false;\">(.*?)</a></td>\s*<td[^>]*>(.*?)</td>\s*<td[^>]*><a[^>]*>(.*?)</a>", x, re.S)
        if not r or r == prev:
            break
        prev = r
        rows += [(n, a.rstrip(' .')) for n, st, a in r if '영업중' in st]
    return C.need(rows, 200, '할리스')
