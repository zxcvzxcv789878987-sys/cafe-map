# 교통안전공단 주차정보(실시간 주차면수를 주는 주차장)의 위치와 이름을 모아 중계 서버 파일로 만든다(2026-11-28).
# 실시간 정보(PrkRealtimeInfo_v1)에는 주차장 번호만 있어서, 시설정보(PrkSttusInfo_v1, 전국 194만 줄)에서 그 번호의 위치와 이름을 찾는다.
#  시설정보는 전국을 한 번에 넘기면 15,000줄 뒤부터 시간 초과가 나고, 시군구로 나누면 실시간 주차장 상당수(수원, 화성 등)가 빠진다.
#  어느 한 방법으로는 다 안 나와서 세 가지를 합친다(2026-11-29 실험: 전국 앞 15쪽 774곳, 시도별 공영 568곳, 시군구별 677곳).
#   1) 나누지 않고 앞에서부터(15쪽쯤에서 시간 초과가 나면 멈춘다) 2) 시도마다 공영이 끝나는 쪽까지 3) 시군구마다 그 시군구 실시간 번호가 다 나올 때까지.
#  번호 가운데 칸이 19299, 19999 같은 곳 상당수는 민영 묶음(전국 190만 줄) 깊은 곳에 있어 아직 못 찾는다.
# 결과: 카페지도-서버/src/kotsa_parks.js  export const KT = { 주차장 번호: [위도*1e5, 경도*1e5, 이름, 공영 1 | 민영 0] }
# 주소: https://apis.data.go.kr/B553881/Parking_v1/{PrkSttusInfo_v1, PrkRealtimeInfo_v1} (끝에 _v1이 붙는다)
# 실행: python -I -X utf8 kotsa_parks.py   (공공데이터 키는 datago_key.txt, 화면에 찍지 않는다. 쪽마다 10~50초라 10분쯤)
import json, os, sys, time, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
KEYF = os.path.join(HERE, 'datago_key.txt')
if not os.path.exists(KEYF):   # worktree에서 돌릴 때는 바탕화면 폴더의 키
    KEYF = r'C:/Users/류도현/OneDrive/Desktop/카페지도/데이터 만들기/datago_key.txt'
KEY = open(KEYF, encoding='utf-8').read().strip()
OUT = r'C:/Users/류도현/OneDrive/Desktop/카페지도-서버/src/kotsa_parks.js'
# 시도 번호(2026-11 법정구역 기준. 전남광주통합특별시 12, 강원 51, 전북 52). 예전 번호도 넣어 두고 비면 넘어간다.
SIDO = ['11', '26', '27', '28', '30', '31', '36', '41', '43', '44', '47', '48', '50', '51', '52', '12', '29', '46', '42', '45']


def call(op, page, rows=1000, **kw):
    q = dict(serviceKey=KEY, pageNo=page, numOfRows=rows, format=2, **kw)
    u = 'https://apis.data.go.kr/B553881/Parking_v1/%s_v1?%s' % (op, urllib.parse.urlencode(q))
    for t in range(4):
        try:
            return json.loads(urllib.request.urlopen(u, timeout=120).read().decode('utf-8', 'replace'))
        except Exception:
            time.sleep(3 + 5 * t)
    return None


# 1. 실시간 주차장 번호 전부
want, page = set(), 1
while True:
    d = call('PrkRealtimeInfo', page)
    rows = (d or {}).get('PrkRealtimeInfo') or []
    want |= {x['prk_center_id'] for x in rows}
    if len(rows) < 1000:
        break
    page += 1
print('실시간 번호', len(want), flush=True)
if len(want) < 500:
    raise SystemExit('실시간 번호가 너무 적다')

found, calls = {}, 0


def take(x):
    k = x.get('prk_center_id')
    if k in want and k not in found:
        try:
            la, lo = float(x.get('prk_plce_entrc_la') or 0), float(x.get('prk_plce_entrc_lo') or 0)
        except ValueError:
            la = lo = 0
        if 33 < la < 39 and 124 < lo < 132:
            found[k] = [round(la * 1e5), round(lo * 1e5), (x.get('prk_plce_nm') or '').strip(), 1 if x.get('prk_manage_agent_nm') == '공영' else 0]
            return 1
    return 0


# 1) 나누지 않고 앞에서부터
for page in range(1, 25):
    d = call('PrkSttusInfo', page); calls += 1
    rows = (d or {}).get('PrkSttusInfo') or []
    if not rows:
        break
    for x in rows:
        take(x)
print('전국 앞쪽', page, '누적', len(found), flush=True)

# 2) 시도마다 공영 묶음을 넘기며 위치를 찾는다
for sd in SIDO:
    page, got = 1, 0
    while page <= 12:
        d = call('PrkSttusInfo', page, sidoCd=sd); calls += 1
        rows = (d or {}).get('PrkSttusInfo') or []
        pub = 0
        for x in rows:
            if x.get('prk_manage_agent_nm') == '공영':
                pub += 1
            got += take(x)
        if d is None or len(rows) < 1000 or pub == 0:
            break
        page += 1
    print(sd, '쪽', page, '찾음', got, '누적', len(found), flush=True)

# 3) 시군구마다(법정구역 시군구 자료) 그 시군구 실시간 번호가 다 나올 때까지
import io, struct, zipfile
ZIP = r'C:/Users/류도현/OneDrive/Desktop/카페지도/데이터 만들기/작업/법정구역/AL_D001_00_20261109.zip'
if os.path.exists(ZIP):
    z = zipfile.ZipFile(ZIP)
    inner = zipfile.ZipFile(io.BytesIO(z.read([n for n in z.namelist() if '(SIG)' in n][0])))
    b = inner.read([n for n in inner.namelist() if n.lower().endswith('.dbf')][0])
    nrec, hlen, rlen = struct.unpack('<IHH', b[4:12])
    sigs = [b[hlen + r * rlen + 1 + 9:hlen + r * rlen + 1 + 14].decode() for r in range(nrec)]   # A0(9) 다음 A1(5)이 시군구 번호
    for code in sigs:
        d = call('PrkRealtimeInfo', 1, sidoCd=code[:2], sigunguCd=code); calls += 1
        left = {x['prk_center_id'] for x in ((d or {}).get('PrkRealtimeInfo') or [])} - set(found)
        page = 1
        while left and page <= 30:
            d = call('PrkSttusInfo', page, sidoCd=code[:2], sigunguCd=code); calls += 1
            rows = (d or {}).get('PrkSttusInfo') or []
            for x in rows:
                if take(x):
                    left.discard(x['prk_center_id'])
                elif x.get('prk_center_id') in left:
                    left.discard(x['prk_center_id'])
            if len(rows) < 1000:
                break
            page += 1
    print('시군구까지 누적', len(found), flush=True)

if len(found) < 500:
    raise SystemExit('너무 적다(%d)' % len(found))
with open(OUT, 'w', encoding='utf-8', newline='') as f:
    f.write('// 교통안전공단 주차정보: 실시간 주차면수를 주는 주차장의 위치와 이름(데이터 만들기/kotsa_parks.py가 만든다, %s).\n' % time.strftime('%Y-%m-%d'))
    f.write('// { 주차장 번호: [위도*1e5, 경도*1e5, 이름, 공영 1 | 민영 0] }\n')
    f.write('export const KT = ' + json.dumps(found, ensure_ascii=False, separators=(',', ':')) + ';\n')
print('실시간 번호', len(want), '위치 찾음', len(found), '호출', calls, '파일 %.0fKB' % (os.path.getsize(OUT) / 1e3))
