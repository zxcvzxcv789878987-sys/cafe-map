# 카페인중독 본사 매장 목록 받기. run_all.py가 불러 쓴다(csv는 run_all.py가 쓴다).
import os, re, importlib.util
_s = importlib.util.spec_from_file_location('_hq_common', os.path.join(os.path.dirname(os.path.abspath(__file__)), '_common.py'))
C = importlib.util.module_from_spec(_s); _s.loader.exec_module(C)

SOURCE = 'https://xn--iq1bo78ac9at1k9mh.com/34'


def fetch():
    B = 'https://xn--iq1bo78ac9at1k9mh.com'
    ids = []
    for p in range(1, 60):
        s = C.get('%s/34/?page=%d' % (B, p))
        new = [i for i in dict.fromkeys(re.findall(r'idx=(\d+)', s)) if i not in ids]
        if not new:
            break
        ids += new
    rows = []
    for i in ids:
        t = C.text('%s/34/?bmode=view&idx=%s&t=board' % (B, i))
        m = re.search(r'가맹점명 (.*?) 매장번호 .*? 매장주소 (.*?) 영업시간', t)
        if m and m.group(2).strip() and not re.search(r'상담중|오픈예정|오픈 예정', m.group(1)):
            rows.append((m.group(1), m.group(2)))
    return C.need(rows, 100, '카페인중독')
