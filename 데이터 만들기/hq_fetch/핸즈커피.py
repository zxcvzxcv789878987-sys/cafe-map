# 핸즈커피 본사 매장 목록 받기. run_all.py가 불러 쓴다(csv는 run_all.py가 쓴다).
import os, re, importlib.util
_s = importlib.util.spec_from_file_location('_hq_common', os.path.join(os.path.dirname(os.path.abspath(__file__)), '_common.py'))
C = importlib.util.module_from_spec(_s); _s.loader.exec_module(C)

SOURCE = 'https://handscoffee.com/new_hands/store/sub1-1.php'


def fetch():
    rows = []
    for p in range(1, 40):
        s = C.get('https://handscoffee.com/new_hands/store/sub1-1.php?m_no=1&s_no=5&bo_table=&page=%d' % p)
        r = re.findall(r"class='tit_weight'>.*?title=\"(.*?)\".*?class='bright'>(.*?)</td>", s, re.S)
        if not r:
            break
        rows += r
    return C.need(rows, 20, '핸즈커피')
