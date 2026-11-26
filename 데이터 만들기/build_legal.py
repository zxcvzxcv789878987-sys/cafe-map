# 법정동, 법정리 이름으로 검색하면 그곳으로 가게 하는 목록(legal.js)을 만든다.
# 자료: 국토교통부 브이월드 "법정구역정보"(dsId=21, 전체데이터 SHP, 라이선스 CC BY 출처 표시).
#  받는 곳: https://www.vworld.kr/dtmk/dtmk_ntads_s002.do?svcCde=NA&dsId=21 (로그인 필요)
#  받은 zip 안에 (SIG) 시군구, (EMD) 법정 읍면동, (LIO) 법정리 zip이 들어 있다.
# 좌표는 EPSG:5186(GRS80, 원점 127E 38N, 축척 1, 가산 200,000 / 600,000). pyproj를 쓸 수 없어 역변환을 직접 계산한다.
# 경계선은 올리지 않고, 이름, 시군구, 안쪽 한 점, 네모 범위만 올린다.
# 사용법: python -X utf8 build_legal.py <AL_D001_..._YYYYMMDD.zip> <출력 legal.js>
import sys, io, os, math, json, zipfile, tempfile
import shapefile
from shapely.geometry import shape

A, F = 6378137.0, 1 / 298.257222101
LAT0, LON0, K0, FE, FN = math.radians(38), math.radians(127.0), 1.0, 200000.0, 600000.0
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
    return math.degrees(lon), math.degrees(lat)


# 앱(index.html의 SIDO_SHORT)과 같은 시도 줄임말
SIDO_SHORT = {'서울특별시': '서울', '경기도': '경기', '인천광역시': '인천', '강원특별자치도': '강원', '대전광역시': '대전', '세종특별자치시': '세종',
              '충청북도': '충북', '충청남도': '충남', '전남광주통합특별시': '광주·전남', '광주광역시': '광주', '전라남도': '전남',
              '전북특별자치도': '전북', '부산광역시': '부산', '대구광역시': '대구', '울산광역시': '울산', '경상북도': '경북',
              '경상남도': '경남', '제주특별자치도': '제주'}
SIDO_CODE = {'11': '서울', '26': '부산', '27': '대구', '28': '인천', '29': '광주·전남', '46': '광주·전남', '12': '광주·전남',
             '30': '대전', '31': '울산', '36': '세종', '41': '경기', '42': '강원', '51': '강원', '43': '충북', '44': '충남',
             '45': '전북', '52': '전북', '47': '경북', '48': '경남', '50': '제주'}


def layer(z, tmp, tag):
    inner = [n for n in z.namelist() if n.endswith('(%s).zip' % tag)][0]
    zz = zipfile.ZipFile(io.BytesIO(z.read(inner)))
    zz.extractall(os.path.join(tmp, tag))
    base = [n for n in zz.namelist() if n.endswith('.shp')][0][:-4]
    return shapefile.Reader(os.path.join(tmp, tag, base), encoding='cp949')


def main(src, out):
    z = zipfile.ZipFile(src)
    tmp = tempfile.mkdtemp()
    sig = {}
    for rec in layer(z, tmp, 'SIG').records():
        a = rec.as_dict()
        parts = a['A2'].split()
        # 원본의 시도 이름은 틀리거나 옛것일 때가 있다("전북특별차지도", "제주도"). 시군구 코드 앞 두 자리로 정한다.
        sido = SIDO_CODE.get(a['A1'][:2]) or SIDO_SHORT.get(parts[0], parts[0])
        # 앱의 지역 단계와 같게: 세종은 "세종 > 세종특별자치시 > 동"이다.
        sig[a['A1']] = '세종 세종특별자치시' if sido == '세종' else ' '.join([sido] + parts[1:])
    groups, gidx = [], {}
    rows, emd_row = [], {}

    def add(sr, code5, up):
        a = sr.record.as_dict()
        g = shape(sr.shape.__geo_interface__)
        if g.is_empty:
            return None
        p = g.representative_point()
        cx, cy = to_lonlat(p.x, p.y)
        x0, y0, x1, y1 = g.bounds
        xs, ys = zip(*[to_lonlat(x, y) for x, y in ((x0, y0), (x0, y1), (x1, y0), (x1, y1))])
        path = sig.get(code5, '')
        if path not in gidx:
            gidx[path] = len(groups)
            groups.append(path)
        rows.append([a['A2'], gidx[path], up, round(cx * 1e5), round(cy * 1e5),
                     round(min(xs) * 1e5), round(min(ys) * 1e5), round(max(xs) * 1e5), round(max(ys) * 1e5)])
        return len(rows) - 1

    for sr in layer(z, tmp, 'EMD').iterShapeRecords():
        a = sr.record.as_dict()
        # A4는 시 단위 코드(수원시 41110)라 구가 빠진다. 법정동 코드 앞 다섯 자리가 시군구(장안구 41111)다.
        k = add(sr, a['A1'][:5], -1)
        if k is not None:
            emd_row[a['A1']] = k
    nli = 0
    for sr in layer(z, tmp, 'LIO').iterShapeRecords():
        a = sr.record.as_dict()
        if add(sr, a['A1'][:5], emd_row.get(a['A1'][:8], -1)) is not None:
            nli += 1
    # 작게 담기: 이름은 | 로 이은 글자 하나, 숫자는 칸마다 한 줄씩. 네모 범위는 안쪽 점에서 떨어진 거리로 적는다.
    pack = {'src': os.path.basename(src), 'g': groups, 'n': '|'.join(r[0] for r in rows),
            'gi': [r[1] for r in rows], 'up': [r[2] for r in rows],
            'c': [v for r in rows for v in (r[3], r[4])],
            'b': [v for r in rows for v in (r[3] - r[5], r[4] - r[6], r[7] - r[3], r[8] - r[4])]}
    js = 'window.LEGAL=' + json.dumps(pack, ensure_ascii=False, separators=(',', ':')) + ';\n'
    open(out, 'w', encoding='utf-8').write(js)
    print('시군구', len(groups), '읍면동', len(emd_row), '리', nli, '크기', len(js.encode()) // 1024, 'KB')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
