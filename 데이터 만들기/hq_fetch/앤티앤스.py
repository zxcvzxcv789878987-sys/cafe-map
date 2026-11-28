# 앤티앤스 본사 매장 목록 받기. run_all.py가 불러 쓴다(csv는 run_all.py가 쓴다).
import os, re, importlib.util
_s = importlib.util.spec_from_file_location('_hq_common', os.path.join(os.path.dirname(os.path.abspath(__file__)), '_common.py'))
C = importlib.util.module_from_spec(_s); _s.loader.exec_module(C)

SOURCE = 'https://www.auntieannes.co.kr/store-map/'


def fetch():
    # 본사 목록은 한 번에 10곳만 보여 주고 쪽 넘김이 안 된다. 시군구와 검색어로 나눠 묻는다.
    Q = C.urllib.parse.quote
    res = {}
    def q(sd, gu, kw=''):
        s = C.get('https://www.auntieannes.co.kr/store-map/?mode=LIST_FORM&nowPage=1&s_sido=%s&s_gugun=%s&s_string=%s' % (Q(sd), Q(gu), Q(kw)))
        for i, n, a in re.findall(r"viewMap\('(\d+)','(.*?)','(.*?)'", s):
            if re.search('[가-힣]', a):
                res[i] = (n, a.strip())
    M = {'강원특별자치도': ['강원도'], '전북특별자치도': ['전라북도'], '전남광주통합특별시': ['광주광역시', '전라남도']}
    sgg, _ = C.regions()
    pairs = []
    for sd, sg in sgg:
        for x in M.get(sd, [sd]):
            if (x, sg.split()[0]) not in pairs:
                pairs.append((x, sg.split()[0]))
    for sd, gu in pairs:
        q(sd, gu)
    for sd in ['서울특별시', '인천광역시', '대전광역시', '대구광역시', '부산광역시', '광주광역시', '울산광역시', '경기도', '강원도',
               '충청북도', '충청남도', '경상북도', '경상남도', '전라북도', '전라남도', '세종특별자치시', '제주특별자치도', '']:
        for kw in ['', '점', '이마트', '롯데', '홈플러스', '현대', '신세계', '역', '트레이더스', '휴게소', '아울렛', '백화점', '터미널', '공항', '몰']:
            q(sd, '', kw)
    return C.need(list(res.values()), 100, '앤티앤스')
