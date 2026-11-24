# 행정안전부 "구역의 도형"(시도별 zip 16개)에서 행정동 경계(TL_SCCO_GEMD)를 꺼내 geojson 하나로 만든다.
# build_shapes.py가 읽는 모양(properties: sidonm, sggnm, adm_nm)에 맞춘다.
# 사용법: python -X utf8 juso_dong.py <zip이 든 폴더> <출력 geojson>
# 좌표는 EPSG:5179(GRS80, 중부원점 127.5E 38N, 축척 0.9996, 가산 1,000,000 / 2,000,000)라서 경위도로 바꾼다.
# 좌표 변환 도구(pyproj)를 쓸 수 없는 컴퓨터라서 횡단 메르카토르 역변환을 직접 계산한다.
import sys, os, io, json, math, zipfile, collections
import shapefile

A, F = 6378137.0, 1 / 298.257222101
LAT0, LON0, K0, FE, FN = math.radians(38), math.radians(127.5), 0.9996, 1000000.0, 2000000.0
E2 = F * (2 - F)
EP2 = E2 / (1 - E2)


def meridian(phi):
    e4, e6 = E2 * E2, E2 ** 3
    return A * ((1 - E2 / 4 - 3 * e4 / 64 - 5 * e6 / 256) * phi - (3 * E2 / 8 + 3 * e4 / 32 + 45 * e6 / 1024) * math.sin(2 * phi)
                + (15 * e4 / 256 + 45 * e6 / 1024) * math.sin(4 * phi) - (35 * e6 / 3072) * math.sin(6 * phi))


M0 = meridian(LAT0)
E1 = (1 - math.sqrt(1 - E2)) / (1 + math.sqrt(1 - E2))


def to_lonlat(x, y):
    m = M0 + (y - FN) / K0
    mu = m / (A * (1 - E2 / 4 - 3 * E2 * E2 / 64 - 5 * E2 ** 3 / 256))
    p1 = (mu + (3 * E1 / 2 - 27 * E1 ** 3 / 32) * math.sin(2 * mu) + (21 * E1 * E1 / 16 - 55 * E1 ** 4 / 32) * math.sin(4 * mu)
          + (151 * E1 ** 3 / 96) * math.sin(6 * mu) + (1097 * E1 ** 4 / 512) * math.sin(8 * mu))
    s, c, t = math.sin(p1), math.cos(p1), math.tan(p1)
    c1, t1 = EP2 * c * c, t * t
    n1 = A / math.sqrt(1 - E2 * s * s)
    r1 = A * (1 - E2) / (1 - E2 * s * s) ** 1.5
    d = (x - FE) / (n1 * K0)
    lat = p1 - (n1 * t / r1) * (d * d / 2 - (5 + 3 * t1 + 10 * c1 - 4 * c1 * c1 - 9 * EP2) * d ** 4 / 24
                                + (61 + 90 * t1 + 298 * c1 + 45 * t1 * t1 - 252 * EP2 - 3 * c1 * c1) * d ** 6 / 720)
    lon = LON0 + (d - (1 + 2 * t1 + c1) * d ** 3 / 6 + (5 - 2 * c1 + 28 * t1 - 3 * c1 * c1 + 8 * EP2 + 24 * t1 * t1) * d ** 5 / 120) / c
    return round(math.degrees(lon), 6), round(math.degrees(lat), 6)


def reader(z, names, layer):
    def g(ext):
        return io.BytesIO(z.read([n for n in names if n.endswith(layer + ext)][0]))
    return shapefile.Reader(shp=g('.shp'), dbf=g('.dbf'), shx=g('.shx'), encoding='cp949')


def main(src, out):
    feats, stat = [], collections.Counter()
    for fn in sorted(os.listdir(src)):
        if not fn.endswith('.zip'):
            continue
        z = zipfile.ZipFile(os.path.join(src, fn))
        names = z.namelist()
        sido = {r['CTPRVN_CD']: r['CTP_KOR_NM'] for r in (x.as_dict() for x in reader(z, names, 'TL_SCCO_CTPRVN').records())}
        sig = {r['SIG_CD']: r['SIG_KOR_NM'] for r in (x.as_dict() for x in reader(z, names, 'TL_SCCO_SIG').records())}
        rd = reader(z, names, 'TL_SCCO_GEMD')
        for sr in rd.iterShapeRecords():
            a = sr.record.as_dict()
            code = a['EMD_CD']
            sidonm, sggnm = sido.get(code[:2], ''), sig.get(code[:5], '')
            gj = sr.shape.__geo_interface__
            def conv(ring):
                return [list(to_lonlat(px, py)) for px, py in ring]
            if gj['type'] == 'Polygon':
                co = [conv(r) for r in gj['coordinates']]
            else:
                co = [[conv(r) for r in poly] for poly in gj['coordinates']]
            feats.append({'type': 'Feature', 'properties': {'sidonm': sidonm, 'sggnm': sggnm, 'adm_nm': (sidonm + ' ' + sggnm + ' ' + a['EMD_KOR_NM']).replace('  ', ' '), 'adm_cd': code},
                          'geometry': {'type': gj['type'], 'coordinates': co}})
            stat[sidonm] += 1
    json.dump({'type': 'FeatureCollection', 'features': feats}, open(out, 'w', encoding='utf-8'), ensure_ascii=False)
    print('행정동', len(feats))
    for k, n in stat.items():
        print(' ', k, n)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
