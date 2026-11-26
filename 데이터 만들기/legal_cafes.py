# 카페마다 법정동(법정 읍면동)을 붙인다. 새 동네 지도와 새 동네 보너스가 법정동으로 센다(사용자 2026-11-27).
# 자료: 국토교통부 브이월드 법정구역정보(build_legal.py와 같은 zip). 카페의 공공데이터 좌표(건물 점)가 어느 법정동 경계 안에 있는지 본다.
# cafes.js(와 있으면 cafes.local.js)에 두 칸을 더한다.
#   ldk: 법정동 이름표 목록("경기 수원시 장안구 이목동", legal.js의 시군구 이름과 같은 꼴)
#   ld:  카페마다 ldk 안의 번호
# 사용법: python -X utf8 legal_cafes.py <AL_D001_..._YYYYMMDD.zip> <cafes.js> [cafes.local.js]
import sys, os, json, math, zipfile, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '작업', 'pylib'))   # shapely, pyshp, numpy(갱신 프로그램이 -I로 돌려서 PYTHONPATH를 못 쓴다)
import numpy as np
import shapely
from shapely.geometry import shape
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_legal import layer, SIDO_CODE, SIDO_SHORT, A, E2, EP2, M0, E1, K0, FE, FN, LON0


def to_lonlat_np(xy):
    """build_legal.to_lonlat과 같은 계산을 배열로(경계 좌표가 많아서)."""
    x, y = xy[:, 0], xy[:, 1]
    m = M0 + (y - FN) / K0
    mu = m / (A * (1 - E2 / 4 - 3 * E2 * E2 / 64 - 5 * E2 ** 3 / 256))
    p1 = (mu + (3 * E1 / 2 - 27 * E1 ** 3 / 32) * np.sin(2 * mu) + (21 * E1 * E1 / 16 - 55 * E1 ** 4 / 32) * np.sin(4 * mu)
          + (151 * E1 ** 3 / 96) * np.sin(6 * mu) + (1097 * E1 ** 4 / 512) * np.sin(8 * mu))
    s, c, t = np.sin(p1), np.cos(p1), np.tan(p1)
    c1, t1 = EP2 * c * c, t * t
    n1 = A / np.sqrt(1 - E2 * s * s)
    r1 = A * (1 - E2) / (1 - E2 * s * s) ** 1.5
    d = (x - FE) / (n1 * K0)
    lat = p1 - (n1 * t / r1) * (d * d / 2 - (5 + 3 * t1 + 10 * c1 - 4 * c1 * c1 - 9 * EP2) * d ** 4 / 24
                                + (61 + 90 * t1 + 298 * c1 + 45 * t1 * t1 - 252 * EP2 - 3 * c1 * c1) * d ** 6 / 720)
    lon = LON0 + (d - (1 + 2 * t1 + c1) * d ** 3 / 6 + (5 - 2 * c1 + 28 * t1 - 3 * c1 * c1 + 8 * EP2 + 24 * t1 * t1) * d ** 5 / 120) / c
    return np.column_stack([np.degrees(lon), np.degrees(lat)])


def load(path):
    s = open(path, encoding='utf-8').read()
    return json.loads(s[s.index('{'):s.rindex('}') + 1])


def save(path, d):
    with open(path, 'w', encoding='utf-8') as o:
        o.write('window.CAFES=')
        json.dump(d, o, ensure_ascii=False, separators=(',', ':'))
        o.write(';')


def main(src, cafes, local=None):
    z = zipfile.ZipFile(src)
    tmp = tempfile.mkdtemp()
    sig = {}
    for rec in layer(z, tmp, 'SIG').records():
        a = rec.as_dict()
        parts = a['A2'].split()
        sido = SIDO_CODE.get(a['A1'][:2]) or SIDO_SHORT.get(parts[0], parts[0])
        sig[a['A1']] = '세종 세종특별자치시' if sido == '세종' else ' '.join([sido] + parts[1:])
    keys, polys = [], []
    for sr in layer(z, tmp, 'EMD').iterShapeRecords():
        a = sr.record.as_dict()
        g = shape(sr.shape.__geo_interface__)
        if g.is_empty:
            continue
        if not g.is_valid:
            g = g.buffer(0)
        g = shapely.transform(g.simplify(3, preserve_topology=True), to_lonlat_np)
        keys.append(sig.get(a['A1'][:5], '') + ' ' + a['A2'])
        polys.append(g)
    tree = shapely.STRtree(polys)
    D = load(cafes)
    lon = np.array(D['lng'], dtype=float) / 1e5
    lat = np.array(D['lat'], dtype=float) / 1e5
    pts = shapely.points(lon, lat)
    hit = np.full(len(pts), -1, dtype=np.int64)
    pi, gi = tree.query(pts, predicate='intersects')
    hit[pi] = gi                      # 경계 위에 걸친 점은 둘 중 하나(나중 것)
    miss = np.where(hit < 0)[0]
    if len(miss):                     # 바다 위나 경계 밖에 찍힌 점은 가장 가까운 동
        mi, mg = tree.query_nearest(pts[miss], return_distance=False)
        hit[miss[mi]] = mg
    used = sorted(set(int(h) for h in hit))
    ix = {h: n for n, h in enumerate(used)}
    ldk = [keys[h] for h in used]
    ld = [ix[int(h)] for h in hit]
    for path in [cafes] + ([local] if local and os.path.exists(local) else []):
        d = D if path == cafes else load(path)
        if len(d['name']) != len(ld):
            print('건너뜀(카페 수가 다름)', path)
            continue
        d['ldk'], d['ld'] = ldk, ld
        save(path, d)
        print('저장', path, '법정동', len(ldk), '경계 밖이라 가까운 동으로', len(miss))


if __name__ == '__main__':
    main(*sys.argv[1:4])
