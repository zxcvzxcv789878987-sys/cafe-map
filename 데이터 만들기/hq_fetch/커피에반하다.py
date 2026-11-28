# 커피에반하다 본사 매장 목록 받기. run_all.py가 불러 쓴다(csv는 run_all.py가 쓴다).
import os, re, importlib.util
_s = importlib.util.spec_from_file_location('_hq_common', os.path.join(os.path.dirname(os.path.abspath(__file__)), '_common.py'))
C = importlib.util.module_from_spec(_s); _s.loader.exec_module(C)

SOURCE = 'https://coffeebanhada.com/main/store/find.php'


def fetch():
    rows = []
    for sd in '강원 경기 경남 경북 광주 대구 대전 부산 서울 세종 울산 인천 전남 전북 제주 충남 충북'.split():
        for p in range(0, 50):
            s = C.get('https://coffeebanhada.com/main/store/find.php?sido=%s&page_now=%d&page_row=500&page_num=10' % (C.urllib.parse.quote(sd), p))
            x = s[s.find('wrt_tbl'):s.find('</table>', s.find('wrt_tbl'))]
            r = re.findall(r"<tr target='[^']*'><td>.*?</td><td>(.*?)</td><td>(.*?)</td>", x)
            rows += r
            if len(r) < 500:
                break
    return C.need(rows, 200, '커피에반하다')
