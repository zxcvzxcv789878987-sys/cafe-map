# 알레그리아 본사 매장 목록 받기. run_all.py가 불러 쓴다(csv는 run_all.py가 쓴다).
import os, re, importlib.util
_s = importlib.util.spec_from_file_location('_hq_common', os.path.join(os.path.dirname(os.path.abspath(__file__)), '_common.py'))
C = importlib.util.module_from_spec(_s); _s.loader.exec_module(C)

SOURCE = 'https://alegriamall.com/locations.html'


def fetch():
    s = C.get(SOURCE)
    r = [(C.clean(n), C.clean(a.replace('<br>', ' '))) for n, a in
         re.findall(r'class="sub">(.*?)</div>.*?주소</div></th>\s*<td><div class="in">(.*?)</div>', s, re.S)]
    return C.need([(n, a) for n, a in r if '쿠웨이트' not in a and '주식회사' not in n], 2, '알레그리아')
