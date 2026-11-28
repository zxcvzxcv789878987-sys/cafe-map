# 대구 시내버스 배차 표 만들기(2026-11-28)
# 원본: 공공데이터포털 15060936 「대구광역시_시내버스 정류소별_노선별_평균배차간격」 CSV(대구광역시 교통정보운영과, 연간 갱신)
#   받아 둔 곳: 데이터 만들기/원본/대구배차/daegu_gap.csv
# 결과: 카페지도-서버/src/daegu_gap.js (중계 서버가 대구 정류장의 오는 차 없는 노선에 첫차, 막차, 배차를 적을 때 쓴다)
#   TAGO는 대구 노선의 배차 간격을 주지 않아서 이 자료로 채운다.
#
# 모양: S = { 정류소ID(DGB 뗀 숫자): { 노선: [평일, 토요일, 휴일] } }, 각 칸은 [첫차 HHMM, 막차 HHMM, 배차 분]
#        R = { 노선: [평일 배차, 토요일 배차, 휴일 배차] }(정류소 값의 중앙값, 노선 창의 배차 칸과 정류소에 값이 없을 때)
# 요일: 평일은 평일(없으면 공통), 토요일은 토요일(감차), 토요일(1,3,5주), 평일, 공통 순, 휴일은 휴일, 공통, 평일 순.
# 정류소 값이 그 노선 중앙값의 두 배를 넘으면(기점, 종점 둘레에서 운행 횟수가 적어 튀는 값) 중앙값을 쓴다.
import csv, json, os, statistics, collections

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, '원본', '대구배차', 'daegu_gap.csv')
OUT = os.path.join(HERE, '..', '..', '카페지도-서버', 'src', 'daegu_gap.js')

ORDER = {
    0: ['평일', '공통'],
    1: ['토요일(감차)', '토요일(1,3,5주)', '평일', '공통'],
    2: ['휴일', '공통', '평일'],
}

def hm(t):
    t = (t or '').strip()
    if ':' not in t: return 0
    h, m = t.split(':')[:2]
    return int(h) * 100 + int(m)

rows = list(csv.reader(open(SRC, encoding='utf-8-sig')))[1:]
by = collections.defaultdict(dict)      # (정류소, 노선) -> {유형: [첫, 막, 배차]}
for r in rows:
    sid, _, route, _, ty, f, l, _, gap = r[:9]
    try: g = int(float(gap))
    except ValueError: continue
    by[(sid.strip(), route.strip())][ty.strip()] = [hm(f), hm(l), g]

def pick(d, k):
    for ty in ORDER[k]:
        if ty in d: return list(d[ty])
    return None

med = collections.defaultdict(lambda: [[], [], []])
for (sid, route), d in by.items():
    for k in range(3):
        v = pick(d, k)
        if v and v[2] > 0: med[route][k].append(v[2])
R = {route: [int(statistics.median(x)) if x else 0 for x in v] for route, v in med.items()}

S = collections.defaultdict(dict)
fixed = 0
for (sid, route), d in by.items():
    out = []
    for k in range(3):
        v = pick(d, k)
        if not v: out.append(0); continue
        m = R[route][k]
        if m and v[2] > m * 2: v[2] = m; fixed += 1
        out.append(v)
    # 세 요일이 같으면 하나만
    S[sid][route] = out[0] if out[0] == out[1] == out[2] else out

js = ('// 대구 시내버스 배차 표. 데이터 만들기/daegu_gap.py가 만든다(손으로 고치지 않는다).\n'
      '// 원본: 공공데이터포털 15060936 대구광역시_시내버스 정류소별_노선별_평균배차간격(대구광역시 교통정보운영과)\n'
      '// S[정류소][노선] = [첫차, 막차, 배차] 또는 [평일, 토요일, 휴일] 각각 그 모양(0은 그날 운행 없음). R[노선] = [평일, 토요일, 휴일] 배차 중앙값.\n'
      'export const DG_S = ' + json.dumps(S, ensure_ascii=False, separators=(',', ':')) + ';\n'
      'export const DG_R = ' + json.dumps(R, ensure_ascii=False, separators=(',', ':')) + ';\n')
open(OUT, 'w', encoding='utf-8').write(js)
print('정류소', len(S), '정류소-노선', len(by), '노선', len(R), '튀는 값 고침', fixed, '크기', round(len(js.encode()) / 1024), 'KB')
