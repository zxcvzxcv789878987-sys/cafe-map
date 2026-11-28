# 랑데자뷰 본사 매장 목록 받기. run_all.py가 불러 쓴다(csv는 run_all.py가 쓴다).
import os, re, importlib.util
_s = importlib.util.spec_from_file_location('_hq_common', os.path.join(os.path.dirname(os.path.abspath(__file__)), '_common.py'))
C = importlib.util.module_from_spec(_s); _s.loader.exec_module(C)

SOURCE = 'https://www.rendejavous.com/default/findstore.php'


def fetch():
    s = C.get(SOURCE)
    return C.need(re.findall(r'<h1>(.*?)</h1><p>(.*?)</p>', s[s.find('store_list_container'):]), 8, '랑데자뷰')
