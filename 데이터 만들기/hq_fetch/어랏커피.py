# 어랏커피 본사 매장 목록 받기. run_all.py가 불러 쓴다(csv는 run_all.py가 쓴다).
import os, re, importlib.util
_s = importlib.util.spec_from_file_location('_hq_common', os.path.join(os.path.dirname(os.path.abspath(__file__)), '_common.py'))
C = importlib.util.module_from_spec(_s); _s.loader.exec_module(C)

SOURCE = 'https://www.alotcoffee.com'


def fetch():
    s = C.get(SOURCE)
    rows = []
    for p in s.split('reviewBox item swiper-slide')[1:]:
        p = p[:6000]
        n = [C.clean(x) for x in re.findall(r'class="fsize18">(.*?)</span>', p, re.S)]
        a = [C.clean(x) for x in re.findall(r'class="fsize16">(.*?)</span>', p, re.S)]
        n = [x for x in n if x]
        a = [x for x in a if x]
        if n and a and '경쟁력' not in a[0]:
            nm = n[0].split(a[0])[0].strip() if a[0] in n[0] else n[0]
            if len(nm) > 12:
                nm = re.split(r' (?:대구|광주|부산|경남|울산) ', nm)[0]
            rows.append((nm, a[0]))
    return C.need(rows, 5, '어랏커피')
