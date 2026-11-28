# 전국 주차장(전국주차장정보 표준데이터, cafe_info.py --fetch가 받은 작업/info_src/parking.json)을 지도용 작은 파일로 나눈다(2026-11-28).
# 버스정류장(bus_tiles.py)과 같은 칸: 위도, 경도 0.05도(가로세로 약 4~5km). 파일 이름은 park/<위도칸>_<경도칸>.json(칸 = floor(좌표 * 20)).
# 한 줄: [위도*1e5, 경도*1e5, 이름, 무료|유료|혼합(모르면 ''), 공영|민영, {n 면 수, d 운영 요일, w/s/h 평일/토요일/공휴일 시간, f [기본분, 기본요금, 추가분, 추가요금]}]
# 같은 이름이 같은 자리(10m 안)에 두 번 있으면 한 줄만 남긴다.
# 실행: python -I -X utf8 park_tiles.py [parking.json 경로]
import json, os, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, '작업', 'info_src', 'parking.json')
OUT = os.path.join(HERE, '..', 'park')

rows = json.load(open(SRC, encoding='utf-8'))
tiles, seen = {}, set()
for r in rows:
    nm = (r[0] or '').strip()
    la, lo = r[1], r[2]
    if not nm or not (33 < la < 39 and 124 < lo < 132):
        continue
    y, x = round(la * 1e5), round(lo * 1e5)
    key = (nm, y // 10, x // 10)
    if key in seen:
        continue
    seen.add(key)
    fee = r[3] if r[3] in ('무료', '유료', '혼합') else ''
    k = '%d_%d' % (int(la * 20 // 1), int(lo * 20 // 1))
    tiles.setdefault(k, []).append([y, x, nm, fee, r[4] or '', r[5] if len(r) > 5 else {}])

if len(seen) < 10000:
    raise SystemExit('주차장이 너무 적다(%d).' % len(seen))
if os.path.isdir(OUT):
    shutil.rmtree(OUT)
os.makedirs(OUT)
for k, v in tiles.items():
    v.sort(key=lambda a: (a[0], a[1]))
    with open(os.path.join(OUT, k + '.json'), 'w', encoding='utf-8', newline='') as f:
        json.dump(v, f, ensure_ascii=False, separators=(',', ':'))
size = sum(os.path.getsize(os.path.join(OUT, f)) for f in os.listdir(OUT))
print('칸', len(tiles), '주차장', len(seen), '크기 %.1fMB' % (size / 1e6), '가장 큰 칸', max(len(v) for v in tiles.values()))
