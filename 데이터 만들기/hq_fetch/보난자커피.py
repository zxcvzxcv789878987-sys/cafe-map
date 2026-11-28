# 보난자커피 본사 매장 목록 받기. run_all.py가 불러 쓴다(csv는 run_all.py가 쓴다).
import os, re, importlib.util
_s = importlib.util.spec_from_file_location('_hq_common', os.path.join(os.path.dirname(os.path.abspath(__file__)), '_common.py'))
C = importlib.util.module_from_spec(_s); _s.loader.exec_module(C)

SOURCE = 'https://bonanzacoffee.kr/store'


def fetch():
    t = C.text('https://bonanzacoffee.kr/store/')
    t = t[t.find('More Store'):]
    r = re.findall(r'([가-힣][가-힣 ]*?) \| [A-Za-z ]+? ((?:서울|경기|부산|대구|인천|제주|대전|광주|울산)[가-힣0-9 ,\-\(\)]*?)\s+(?=[A-Z0-9][A-Za-z0-9]*[,F ]+[^가-힣]*?(?:ro|gil|daero|Seoul|Busan|Gyeonggi))', t)
    d = {}
    m = re.search(r'군자 \| Gunja ((?:서울)[가-힣0-9A-Z \-]+?층)', t)
    if m:
        d['군자'] = m.group(1)
    for n, a in r:
        d.setdefault(n, re.sub(r'\s+', ' ', a))
    return C.need([(k + '점', v) for k, v in d.items()], 8, '보난자커피')
