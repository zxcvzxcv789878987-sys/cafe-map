# 전국 버스정류장(국토교통부 정류소 목록, 작업/info_src/bus_stops.csv)을 지도용 작은 파일로 나눈다(2026-11-28).
# 지도의 파란 정류장 표시가 OpenStreetMap 자료라 빠진 곳이 많아서(수원 정자동 26%, 강남역 7%) 공공데이터로 직접 그린다.
# 한 칸은 위도, 경도 0.05도(가로세로 약 4~5km). 파일 이름은 bus/<위도칸>_<경도칸>.json(칸 = floor(좌표 * 20)).
# 한 줄: [위도*1e5, 경도*1e5, 이름, 정류장 아이디(nodeid), 도시 코드, 정류장 번호(서울은 arsId)]
# 지나가기만 하는 정류장(이름에 미정차)은 뺀다.
# 실행: python -I -X utf8 bus_tiles.py
import csv, json, os, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, '작업', 'info_src', 'bus_stops.csv')
OUT = os.path.join(HERE, '..', 'bus')

rows = list(csv.reader(open(SRC, encoding='cp949')))[1:]
tiles = {}
for r in rows:
    nm = r[1].strip()
    if not nm or '미정차' in nm:
        continue
    try:
        la, lo = float(r[2]), float(r[3])
    except ValueError:
        continue
    if not (33 < la < 39 and 124 < lo < 132):
        continue
    k = '%d_%d' % (int(la * 20 // 1), int(lo * 20 // 1))
    tiles.setdefault(k, []).append([round(la * 1e5), round(lo * 1e5), nm, r[0], r[6], r[5]])

if os.path.isdir(OUT):
    shutil.rmtree(OUT)
os.makedirs(OUT)
total = 0
for k, v in tiles.items():
    v.sort()
    with open(os.path.join(OUT, k + '.json'), 'w', encoding='utf-8', newline='') as f:
        json.dump(v, f, ensure_ascii=False, separators=(',', ':'))
    total += len(v)
size = sum(os.path.getsize(os.path.join(OUT, f)) for f in os.listdir(OUT))
print('칸', len(tiles), '정류장', total, '크기 %.1fMB' % (size / 1e6), '가장 큰 칸', max(len(v) for v in tiles.values()))
