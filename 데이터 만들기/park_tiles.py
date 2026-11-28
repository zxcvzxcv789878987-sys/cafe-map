# 전국 주차장(전국주차장정보 표준데이터, cafe_info.py --fetch가 받은 작업/info_src/parking.json)을 지도용 작은 파일로 나눈다(2026-11-28).
# 버스정류장(bus_tiles.py)과 같은 칸: 위도, 경도 0.05도(가로세로 약 4~5km). 파일 이름은 park/<위도칸>_<경도칸>.json(칸 = floor(좌표 * 20)).
# 한 줄: [위도*1e5, 경도*1e5, 이름, 무료|유료|혼합(모르면 ''), 공영|민영, {n 면 수, d 운영 요일, w/s/h 평일/토요일/공휴일 시간, f [기본분, 기본요금, 추가분, 추가요금], dp 하루 주차권}]
# 같은 이름이 같은 자리(10m 안)에 두 번 있으면 한 줄만 남긴다.
# 검색 색인(2026-11-28 사용자: 검색 탭에 주차장): parkidx/n<첫 글자 코드>.json.
#  이름을 빈칸과 괄호로 나눈 조각, 빈칸을 뗀 이름, 지역 낱말의 첫 글자 칸에 넣는다(정류장 색인 busidx와 비슷한 방식).
#  한 줄: [이름, 지역(예: 서울 용산구), 무료|유료|혼합, 칸, 칸 안 순번]. 지역은 parking.json 7번째 칸 주소에서 시도와 시군구.
# 실행: python -I -X utf8 park_tiles.py [parking.json 경로]
import json, os, re, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, '작업', 'info_src', 'parking.json')
OUT = os.path.join(HERE, '..', 'park')
IDX = os.path.join(HERE, '..', 'parkidx')

SIDO = {'서울특별시': '서울', '부산광역시': '부산', '대구광역시': '대구', '인천광역시': '인천', '광주광역시': '광주', '대전광역시': '대전',
        '울산광역시': '울산', '세종특별자치시': '세종', '경기도': '경기', '강원특별자치도': '강원', '강원도': '강원', '충청북도': '충북',
        '충청남도': '충남', '전북특별자치도': '전북', '전라북도': '전북', '전라남도': '전남', '경상북도': '경북', '경상남도': '경남',
        '제주특별자치도': '제주', '전남광주통합특별시': '전남광주'}


def area(addr):
    """주소 앞머리를 '서울 용산구', '경기 수원시 팔달구'처럼. 모르는 모양이면 ''."""
    t = (addr or '').split()
    if not t or t[0] not in SIDO:
        return ''
    out = [SIDO[t[0]]]
    for w in t[1:3]:
        if re.search(r'(시|군|구)$', w) and not re.search(r'\d', w):
            out.append(w)
        else:
            break
    return ' '.join(out)


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
    tiles.setdefault(k, []).append([[y, x, nm, fee, r[4] or '', r[5] if len(r) > 5 else {}], area(r[6] if len(r) > 6 else '')])

if len(seen) < 10000:
    raise SystemExit('주차장이 너무 적다(%d).' % len(seen))
for d in (OUT, IDX):
    if os.path.isdir(d):
        shutil.rmtree(d)
    os.makedirs(d)
shards = {}
for k, v in tiles.items():
    v.sort(key=lambda a: (a[0][0], a[0][1]))
    with open(os.path.join(OUT, k + '.json'), 'w', encoding='utf-8', newline='') as f:
        json.dump([a[0] for a in v], f, ensure_ascii=False, separators=(',', ':'))
    for j, (s, ar) in enumerate(v):
        heads = set()
        # 지역 낱말(서울, 용산구)도 넣는다: "용산 주차장"처럼 동네로 찾으면 이름에 동네가 없는 주차장도 나오게.
        for part in [s[2].replace(' ', '')] + re.split(r'[\s()\[\]]+', s[2]) + ar.split():
            part = part.strip().lower()
            if part:
                heads.add(part[0])
        for h in heads:
            shards.setdefault('n%x' % ord(h), []).append([s[2], ar, s[3], k, j])
for k, v in shards.items():
    with open(os.path.join(IDX, k + '.json'), 'w', encoding='utf-8', newline='') as f:
        json.dump(v, f, ensure_ascii=False, separators=(',', ':'))
size = sum(os.path.getsize(os.path.join(OUT, f)) for f in os.listdir(OUT))
isz = sum(os.path.getsize(os.path.join(IDX, f)) for f in os.listdir(IDX))
print('칸', len(tiles), '주차장', len(seen), '크기 %.1fMB' % (size / 1e6), '가장 큰 칸', max(len(v) for v in tiles.values()))
print('색인 파일', len(shards), '크기 %.1fMB' % (isz / 1e6), '가장 큰 파일 %.0fKB' % (max(os.path.getsize(os.path.join(IDX, f)) for f in os.listdir(IDX)) / 1e3),
      '지역 없음', sum(1 for v in tiles.values() for a in v if not a[1]))
