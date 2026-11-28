# 커피빈 본사 매장 목록 받기. run_all.py가 불러 쓴다(csv는 run_all.py가 쓴다).
import os, re, importlib.util
_s = importlib.util.spec_from_file_location('_hq_common', os.path.join(os.path.dirname(os.path.abspath(__file__)), '_common.py'))
C = importlib.util.module_from_spec(_s); _s.loader.exec_module(C)

SOURCE = 'https://www.coffeebeankorea.com/store/store.asp'


def fetch():
    H = {'Referer': 'https://www.coffeebeankorea.com/store/store.asp', 'X-Requested-With': 'XMLHttpRequest'}
    chk = '&'.join('chk%d=0' % i for i in range(1, 14))
    s = C.get('https://www.coffeebeankorea.com/store/store_data2.asp?lat=36.3&lng=127.8&%s&keyword=&StoreLocal=&StoreLocal2=&storeNo=' % chk, headers=H)
    return C.need(re.findall(r"StoreName : '(.*?)'.*?StoreAddress : '(.*?)'", s), 80, '커피빈')
