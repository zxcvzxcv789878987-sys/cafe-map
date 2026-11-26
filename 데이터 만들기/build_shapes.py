# 행정동 경계(geojson)를 지도의 지역 단계(시도 > 시 > 구)에 맞춰 합치고 단순하게 만들어 regions.js로 저장한다.
# 경계 자료: 행정안전부 주소기반산업지원서비스의 "구역의 도형"(행정동 TL_SCCO_GEMD). juso_dong.py가 geojson으로 바꿔 준다.
# (2026-11-24 전에는 github.com/vuski/admdongkor, 원자료 통계청 SGIS를 썼다.)
# 사용법: python -X utf8 build_shapes.py <행정동 geojson> <cafes.js> <출력 regions.js>
import sys, json, collections, re
from shapely.geometry import shape, Point
from shapely.ops import unary_union
import shapely

geo_path, cafes_path, out_path = sys.argv[1], sys.argv[2], sys.argv[3]

SIDO_SHORT = {'서울특별시': '서울', '경기도': '경기', '인천광역시': '인천', '강원특별자치도': '강원', '대전광역시': '대전',
              '세종특별자치시': '세종', '충청북도': '충북', '충청남도': '충남', '전남광주통합특별시': '광주·전남', '광주광역시': '광주',
              '전라남도': '전남', '전북특별자치도': '전북', '부산광역시': '부산', '대구광역시': '대구', '울산광역시': '울산',
              '경상북도': '경북', '경상남도': '경남', '제주특별자치도': '제주'}


def norm(s):
    # 공식 경계는 "가양제1동", 카페 자료는 "가양1동"처럼 적으므로 숫자 앞의 "제"를 뺀다.
    return re.sub(r'제(\d)', r'\1', s.replace('·', '').replace('.', '').replace(' ', ''))


# 0. 카페 자료의 지역 이름. 경계 자료는 "수원시영통구"처럼 붙여 쓰므로 카페 자료 표기로 맞춘다.
D = json.loads(open(cafes_path, encoding='utf-8').read()[len('window.CAFES='):-1])
SGG_NAME = {(D['sido'][si], norm(n)): n for n, si in D['sgg']}

# 1. 경계를 읽어서 시도, 시군구, 동 이름으로 묶는다.
feats = json.load(open(geo_path, encoding='utf-8'))['features']
by_sido, by_sgg, by_city, by_dong = collections.defaultdict(list), collections.defaultdict(list), collections.defaultdict(list), {}
sido_polys = collections.defaultdict(list)
for f in feats:
    pr = f['properties']
    sido, sgg = pr['sidonm'], pr['sggnm']
    dong = pr['adm_nm'][len(sido) + 1 + len(sgg) + 1:] if pr['adm_nm'].startswith(sido + ' ' + sgg + ' ') else pr['adm_nm'].split()[-1]
    if sido.startswith('세종'):
        sgg = sido
    sgg = SGG_NAME.get((sido, norm(sgg)), sgg)
    g = shape(f['geometry'])
    if not g.is_valid:
        g = g.buffer(0)
    short = SIDO_SHORT.get(sido, sido)
    by_sido[short].append(g)
    by_sgg[short + ' ' + sgg].append(g)
    t = sgg.split(' ')
    if len(t) >= 2:
        by_city[short + ' ' + t[0]].append(g)
    by_dong[(sido, norm(sgg), norm(dong))] = g
    sido_polys[sido].append(g)

# 2. 카페 자료의 지역 목록을 읽는다.
cent = collections.defaultdict(lambda: [0.0, 0.0, 0])
for la, lo, d in zip(D['lat'], D['lng'], D['dongOf']):
    c = cent[d]
    c[0] += lo / 1e5
    c[1] += la / 1e5
    c[2] += 1

TOL = {'sido': 0.003, 'sgg': 0.0007, 'dong': 0.00015}
MIN_PART = {'sido': 2e-4, 'sgg': 4e-5, 'dong': 4e-6}
out, stat = {}, collections.Counter()


def encode(geom, kind):
    """작은 섬은 버리고, 선을 단순하게 한 뒤 좌표를 정수 차이값으로 줄인다."""
    geom = geom.simplify(TOL[kind], preserve_topology=True)
    parts = list(geom.geoms) if geom.geom_type == 'MultiPolygon' else [geom]
    parts = [p for p in parts if p.geom_type == 'Polygon' and not p.is_empty]
    if not parts:
        return None
    big = max(p.area for p in parts)
    parts = [p for p in parts if p.area >= MIN_PART[kind] or p.area >= big * 0.2]
    rings = []
    for p in parts:
        for ring in [p.exterior] + [h for h in p.interiors if shapely.Polygon(h).area >= MIN_PART[kind]]:
            xs = [(round(x * 1e5), round(y * 1e5)) for x, y in ring.coords]
            flat, px, py = [], 0, 0
            for x, y in xs:
                flat += [x - px, y - py]
                px, py = x, y
            rings.append(flat)
    # 이름표를 놓을 자리: 가장 큰 덩어리 안에서 가장 넓은 곳의 가운데
    main = max(parts, key=lambda p: p.area)
    try:
        c = shapely.maximum_inscribed_circle(main)
        lx, ly = c.coords[0]
    except Exception:
        q = main.representative_point()
        lx, ly = q.x, q.y
    return {'p': [round(lx * 1e5), round(ly * 1e5)], 'r': rings}


for path, polys in by_sido.items():
    e = encode(unary_union(polys), 'sido')
    if e:
        out[path] = e
        stat['시도'] += 1
for group, name in ((by_sgg, '시군구'), (by_city, '시')):
    for path, polys in group.items():
        e = encode(unary_union(polys), 'sgg')
        if e:
            out[path] = e
            stat[name] += 1

# 동 단계 경계는 넣지 않는다(2026-11-27). 앱의 동은 법정동이고 그 경계는 legal/<시군구코드>.json(build_legal.py)에 있다.
# 행정동 경계를 남겨 두면 같은 이름의 법정동에 다른 경계가 그려질 수 있다. 옛 행정동 경계가 다시 필요하면 WITH_DONG을 True로.
WITH_DONG = False
for di, (dong, gi) in enumerate(D['dong'] if WITH_DONG else []):
    sgg, si = D['sgg'][gi]
    sido = D['sido'][si]
    g = by_dong.get((sido, norm(sgg), norm(dong)))
    if g is None and cent[di][2]:
        # 이름이 안 맞으면 그 동 카페들의 가운데가 들어 있는 경계를 쓴다.
        pt = Point(cent[di][0] / cent[di][2], cent[di][1] / cent[di][2])
        for cand in sido_polys[sido]:
            if cand.contains(pt):
                g = cand
                stat['동(위치로 맞춤)'] += 1
                break
    if g is None:
        stat['동(못 찾음)'] += 1
        continue
    e = encode(g, 'dong')
    if e:
        out[SIDO_SHORT.get(sido, sido) + ' ' + sgg + ' ' + dong] = e
        stat['동'] += 1

with open(out_path, 'w', encoding='utf-8') as o:
    o.write('window.REGION_SHAPES=')
    json.dump(out, o, ensure_ascii=False, separators=(',', ':'))
    o.write(';')
import os
print(dict(stat), '점 개수', sum(len(r) // 2 for v in out.values() for r in v['r']), '파일', os.path.getsize(out_path))
