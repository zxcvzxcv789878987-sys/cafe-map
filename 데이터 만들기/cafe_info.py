# 카페 카드의 '카페지도 정보' 탭에 붙일 가게 주변 정보를 만든다(사용자 2026-11-28).
# 사용법: python -I -X utf8 cafe_info.py [--fetch]
#   --fetch: 원본 자료를 새로 받는다(refresh.py가 매달 붙여 부른다). 없으면 작업/info_src/에 받아 둔 것으로 만든다.
#
# 넣는 것(모두 공공 자료, 거리는 공개 cafes.js 좌표로 잰 직선 미터)
#   b: 가까운 버스정류장 1km 안. 국토교통부 전국 버스정류장 위치정보(공공데이터포털 파일 15067528)
#      [이름, 미터, 위도x1e5, 경도x1e5, 정류장번호(nodeid, 예: ADB354000317), 도시코드(cityCode), 모바일단축번호]. 빈 끝 칸은 뺀다.
#      b2: 건너편 정류장(같은 이름, 다른 번호, 정류장에서 5m 넘고 300m 안). 모양은 b와 같다.
#      서울(도시코드 11)의 단축번호는 서울시 정류소 번호(arsId, 다섯 자리). 경기 정류장(GGB로 시작)의 경기도 정류소 ID는 GGB 뒤의 숫자.
#   s: 가까운 지하철역 [역 이름, 미터] 1km 안. 전국도시철도역사정보 표준데이터(15013205). 원본은 철도 데이터 포털(data.kric.go.kr)의 엑셀.
#   p: 500m 안 가장 가까운 공영(민영) 주차장 [이름, 미터, 무료|유료|혼합(모르면 ''), {y, x: 위도, 경도 x1e5, n: 주차구획수, d: 운영요일,
#      w, s, h: 평일, 토요일, 공휴일 운영시간 '09:00-18:00', f: [기본시간(분), 기본요금, 추가단위시간(분), 추가단위요금]}]. 빈 칸은 뺀다. 전국주차장정보 표준데이터 API
#   m: 1이면 지역사랑상품권(조폐공사 모바일 가맹점, 음료점 562, 계속사업자) 가맹점. 이름이 비슷하고 150m 안인 곳.
#      사업자등록번호는 받자마자 버리고 어디에도 저장하지 않는다.
#   e, y, c: 건축물대장(승객용 승강기 수, 사용승인 연도, 건물 주차 대수). building_info.py가 작업/info_src/bld.json에 나눠 받아 둔 것을 붙인다.
# 결과: 저장소의 info/<이름표 앞 두 글자>.json = {이름표: {...}}. 이름표는 index.html의 cidOf와 같은 방법(이름|주소의 해시).
import os, sys, re, csv, json, math, time, difflib, collections, urllib.request, urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(HERE, '작업', 'info_src')
OUT = os.path.join(ROOT, 'info')
os.makedirs(SRC, exist_ok=True)
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36'
FETCH = '--fetch' in sys.argv


def key():
    return open(os.path.join(HERE, 'datago_key.txt'), encoding='utf-8').read().strip()


def get_json(url, params, tries=4):
    q = urllib.parse.urlencode(dict(params, serviceKey=key()))
    for t in range(tries):
        try:
            return json.loads(urllib.request.urlopen(urllib.request.Request(url + '?' + q, headers={'User-Agent': UA}), timeout=90).read().decode('utf-8', 'replace'))
        except Exception as e:
            if t == tries - 1:
                raise RuntimeError('%s 받기 실패: %s' % (url, type(e).__name__))
            time.sleep(3 * (t + 1))


def save_json(obj, path):
    json.dump(obj, open(path + '.tmp', 'w', encoding='utf-8'), ensure_ascii=False)
    os.replace(path + '.tmp', path)


# ---------- 원본 받기 ----------
def fetch_bus():
    page = urllib.request.urlopen(urllib.request.Request('https://www.data.go.kr/data/15067528/fileData.do', headers={'User-Agent': UA}), timeout=60).read().decode('utf-8', 'replace')
    m = re.search(r"fn_fileDataDown\('15067528',\s*'(uddi:[0-9a-f-]+)'", page)
    if not m:
        raise RuntimeError('버스정류장 파일 번호를 찾지 못했다(화면이 바뀐 것 같다).')
    body = urllib.parse.urlencode({'publicDataPk': '15067528', 'publicDataDetailPk': m.group(1), 'fileDetailSn': '1'}).encode()
    info = json.load(urllib.request.urlopen(urllib.request.Request('https://www.data.go.kr/tcs/dss/selectFileDataDownload.do', data=body, headers={'User-Agent': UA, 'Referer': 'https://www.data.go.kr/data/15067528/fileData.do'}), timeout=60))
    atch = re.search(r'"atchFileId"\s*:\s*"([^"]+)"', json.dumps(info))
    if not atch:
        raise RuntimeError('버스정류장 파일(atchFileId)을 받지 못했다.')
    data = urllib.request.urlopen(urllib.request.Request('https://www.data.go.kr/cmm/cmm/fileDownload.do?atchFileId=%s&fileDetailSn=1' % atch.group(1), headers={'User-Agent': UA}), timeout=300).read()
    if len(data) < 5 << 20:
        raise RuntimeError('버스정류장 파일이 너무 작다.')
    open(os.path.join(SRC, 'bus_stops.csv.part'), 'wb').write(data)
    os.replace(os.path.join(SRC, 'bus_stops.csv.part'), os.path.join(SRC, 'bus_stops.csv'))
    print('버스정류장 파일', len(data) // (1 << 20), 'MB', flush=True)


def fetch_subway():
    """전국도시철도역사정보 표준데이터 원본(철도 데이터 포털, 국가철도공단). 공공데이터포털 15013205의 '바로가기'가 가리키는 곳."""
    req = urllib.request.Request('https://data.kric.go.kr/rips/dataset/download.file?type=filedata&id=32&operation=1',
                                 headers={'User-Agent': UA, 'Referer': 'https://data.kric.go.kr/rips/M_01_01/detail.do?id=32'})
    data = urllib.request.urlopen(req, timeout=120).read()
    if data[:2] != b'PK' or len(data) < 50000:
        raise RuntimeError('지하철역 파일이 엑셀이 아니거나 너무 작다.')
    open(os.path.join(SRC, 'subway.xlsx.part'), 'wb').write(data)
    os.replace(os.path.join(SRC, 'subway.xlsx.part'), os.path.join(SRC, 'subway.xlsx'))
    print('지하철역 파일', len(data) // 1024, 'KB', flush=True)


def park_extra(it):
    """주차장 작은 창에 쓰는 칸(표준데이터 그대로, 빈 칸은 뺀다).
    n: 주차구획수, d: 운영요일, w/s/h: 평일/토요일/공휴일 운영시간 '시작-끝', f: [기본시간(분), 기본요금, 추가단위시간(분), 추가단위요금]."""
    def num(k):
        try:
            return int(float(it.get(k) or ''))
        except ValueError:
            return None

    def hours(a, b):
        a, b = (it.get(a) or '').strip(), (it.get(b) or '').strip()
        return a + '-' + b if a and b else None
    x = {'n': num('prkcmprt') or None, 'd': (it.get('operDay') or '').strip() or None,
         'w': hours('weekdayOperOpenHhmm', 'weekdayOperColseHhmm'),
         's': hours('satOperOperOpenHhmm', 'satOperCloseHhmm'),
         'h': hours('holidayOperOpenHhmm', 'holidayCloseOpenHhmm')}
    f = [num('basicTime'), num('basicCharge'), num('addUnitTime'), num('addUnitCharge')]
    if any(f[1:]):          # 요금이 하나라도 적힌 곳만(무료 주차장의 기본시간만 있는 줄은 뺀다)
        x['f'] = [v if v is not None else 0 for v in f]
    return {k: v for k, v in x.items() if v}


def fetch_parking():
    url = 'http://api.data.go.kr/openapi/tn_pubr_prkplce_info_api'
    out, page = [], 1
    while True:
        d = get_json(url, {'pageNo': page, 'numOfRows': 1000, 'type': 'json'})
        body = d.get('response', d).get('body', {})
        items = body.get('items') or []
        if isinstance(items, dict):
            items = items.get('item') or []
        for it in items:
            try:
                la, ln = float(it.get('latitude') or 0), float(it.get('longitude') or 0)
            except ValueError:
                continue
            if 33 < la < 39 and 124 < ln < 132:
                out.append([it.get('prkplceNm') or '', round(la, 6), round(ln, 6), it.get('parkingchrgeInfo') or '', it.get('prkplceSe') or '', park_extra(it)])
        total = int(body.get('totalCount') or 0)
        if not items or page * 1000 >= total:
            break
        page += 1
        time.sleep(0.3)
    if len(out) < 10000:
        raise RuntimeError('주차장이 너무 적다(%d).' % len(out))
    save_json(out, os.path.join(SRC, 'parking.json'))
    print('주차장', len(out), flush=True)


def fetch_money():
    url = 'https://apis.data.go.kr/B190001/mobileFranchisesV4/mobileV4'
    out, page = [], 1
    while True:
        d = get_json(url, {'page': page, 'perPage': 1000, 'cond[ksic_cd::EQ]': '562', 'cond[bzmn_stts::EQ]': '01'})
        rows = d.get('data') or []
        for it in rows:
            # 사업자등록번호(brno)는 쓰지 않고 버린다.
            if it.get('lat') and it.get('lot'):
                out.append([it.get('frcs_nm') or '', round(float(it['lat']), 6), round(float(it['lot']), 6)])
        if not rows or page * 1000 >= int(d.get('matchCount') or 0):
            break
        page += 1
        time.sleep(0.3)
    if len(out) < 30000:
        raise RuntimeError('지역화폐 가맹점이 너무 적다(%d).' % len(out))
    save_json(out, os.path.join(SRC, 'money.json'))
    print('지역화폐 음료점 가맹점(영업 중)', len(out), flush=True)


if FETCH:
    # 하나가 실패해도 멈추지 않고 지난번에 받아 둔 자료로 만든다(받아 둔 것도 없으면 그 항목만 빠진다).
    for f in (fetch_bus, fetch_subway, fetch_parking, fetch_money):
        try:
            f()
        except Exception as e:
            print('받기 실패, 지난번 자료로 만든다:', f.__name__, str(e)[:200], flush=True)


# ---------- 읽기 ----------
def read_bus():
    out = []
    raw = open(os.path.join(SRC, 'bus_stops.csv'), 'rb').read()
    for enc in ('utf-8-sig', 'cp949'):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    r = csv.reader(text.splitlines())
    h = next(r)
    ih = {k.strip(): i for i, k in enumerate(h)}
    i_n, i_la, i_ln = ih['정류장명'], ih['위도'], ih['경도']
    i_id, i_ars, i_city, i_cn, i_mg = ih.get('정류장번호'), ih.get('모바일단축번호'), ih.get('도시코드'), ih.get('도시명'), ih.get('관리도시명')
    cell = lambda row, i: row[i].strip() if i is not None and i < len(row) else ''
    for row in r:
        try:
            la, ln = float(row[i_la]), float(row[i_ln])
        except (ValueError, IndexError):
            continue
        if 33 < la < 39 and 124 < ln < 132 and row[i_n].strip():
            city, ars = cell(row, i_city), cell(row, i_ars)
            if city == '11' and ars.isdigit():
                ars = ars.zfill(5)      # 서울 정류소 번호(arsId)는 다섯 자리
            # 자기 지역 BIS가 관리하는 줄인가(서울 정류장이 경기BIS에도 한 번 더 올라 있다. 실시간 도착은 자기 지역 번호가 맞다)
            home = cell(row, i_cn)[:2] == cell(row, i_mg)[:2]
            out.append([row[i_n].strip(), la, ln, cell(row, i_id), city, ars, home])
    return out


def read_subway():
    """사람이 받아 둔 전국도시철도역사정보 표준데이터(csv 또는 xlsx). 역사명과 위도, 경도 칸을 찾는다."""
    rows = None
    for fn in ('subway.csv', 'subway.xlsx'):
        p = os.path.join(SRC, fn)
        if not os.path.exists(p):
            continue
        if fn.endswith('.csv'):
            raw = open(p, 'rb').read()
            for enc in ('utf-8-sig', 'cp949'):
                try:
                    rows = list(csv.reader(raw.decode(enc).splitlines()))
                    break
                except UnicodeDecodeError:
                    continue
        else:
            import openpyxl
            ws = openpyxl.load_workbook(p, read_only=True, data_only=True).active
            rows = [[('' if c is None else str(c)) for c in row] for row in ws.iter_rows(values_only=True)]
        break
    if not rows:
        return []
    hi = next(k for k, row in enumerate(rows[:10]) if any('위도' in c for c in row))
    h = [c.strip() for c in rows[hi]]
    i_n = next(i for i, c in enumerate(h) if c in ('역사명', '역명') or c.endswith('역사명'))
    i_l = next((i for i, c in enumerate(h) if '노선명' in c), None)
    i_la = next(i for i, c in enumerate(h) if '위도' in c)
    i_ln = next(i for i, c in enumerate(h) if '경도' in c)
    out = []
    for row in rows[hi + 1:]:
        try:
            la, ln = float(row[i_la]), float(row[i_ln])
        except (ValueError, IndexError):
            continue
        nm = row[i_n].strip()
        if not nm:
            continue
        if not nm.endswith('역'):
            nm += '역'
        if 33 < la < 39 and 124 < ln < 132:
            out.append([nm, la, ln, row[i_l].strip() if i_l is not None else ''])
    return out


# ---------- 카페와 이름표 ----------
def imul(a, b):
    return ((a & 0xffffffff) * (b & 0xffffffff)) & 0xffffffff


def hash36(s):
    """index.html의 hash36과 같은 값. 자바스크립트 charCodeAt처럼 UTF-16 단위로 센다."""
    h1, h2 = 0xdeadbeef, 0x41c6ce57
    b = s.encode('utf-16-le')
    for k in range(0, len(b), 2):
        ch = b[k] | (b[k + 1] << 8)
        h1 = imul(h1 ^ ch, 2654435761)
        h2 = imul(h2 ^ ch, 1597334677)
    h1 = imul(h1 ^ (h1 >> 16), 2246822507) ^ imul(h2 ^ (h2 >> 13), 3266489909)
    h2 = imul(h2 ^ (h2 >> 16), 2246822507) ^ imul(h1 ^ (h1 >> 13), 3266489909)
    n = 4294967296 * (2097151 & h2) + (h1 & 0xffffffff)
    digits = '0123456789abcdefghijklmnopqrstuvwxyz'
    out = ''
    while True:
        n, r = divmod(n, 36)
        out = digits[r] + out
        if not n:
            return out


s = open(os.path.join(ROOT, 'cafes.js'), encoding='utf-8').read()
D = json.loads(s[s.index('=') + 1:s.rindex(';')])
N = len(D['name'])
cids = []
for i in range(N):
    d = D['dong'][D['dongOf'][i]]
    g = D['sgg'][d[1]]
    sido, sg = D['sido'][g[1]], g[0]
    cids.append(hash36(D['name'][i] + '|' + (sido if sg == sido else sido + ' ' + sg) + ' ' + D['road'][i]))
lat = [v / 1e5 for v in D['lat']]
lng = [v / 1e5 for v in D['lng']]

GS = 0.01


def grid(points):
    g = collections.defaultdict(list)
    for p in points:
        g[(int(p[1] / GS), int(p[2] / GS))].append(p)
    return g


def dist(la, ln, la2, ln2):
    return math.hypot((la - la2) * 111000, (ln - ln2) * 111000 * math.cos(math.radians(la)))


def nearest(g, la, ln, m, ok=None):
    c0, c1 = int(la / GS), int(ln / GS)
    rr = int(m / 111000 / GS) + 1
    best, bd = None, m + 1
    for a in range(c0 - rr, c0 + rr + 1):
        for b in range(c1 - rr, c1 + rr + 1):
            for p in g.get((a, b), ()):
                d = dist(la, ln, p[1], p[2])
                if d < bd and (ok is None or ok(p)):
                    best, bd = p, d
    return best, bd


def norm(n):
    n = re.sub(r'\([^)]*\)', '', n or '')
    return re.sub(r'[^0-9a-z가-힣]', '', n.lower())


FILLER = re.compile(r'카페|커피|coffee|cafe|로스터스|로스터리|베이커리|디저트|점$')


def core(n):
    c = FILLER.sub('', n)
    return c if len(c) >= 2 else n


def similar(a, b):
    if not a or not b:
        return 0.0
    ca, cb = core(a), core(b)
    if len(ca) >= 2 and len(cb) >= 2 and (ca in cb or cb in ca):
        return 1.0
    return max(difflib.SequenceMatcher(None, a, b).ratio(), difflib.SequenceMatcher(None, ca, cb).ratio())


info = [dict() for _ in range(N)]
stat = collections.Counter()

def stem(n):
    """정류장 이름 줄기: 마주 보는 두 정류장이 '신세계병원앞', '신세계병원건너'처럼 꼬리만 다를 때 같게 만든다."""
    n = re.sub(r'\s', '', n).split('.')[0]
    n = re.sub(r'\([^)]*\)', '', n)
    n = re.sub(r'\d+번?출구', '', n)
    return re.sub(r'(건너편|건너|맞은편|앞)?\d*$', '', n)


bus = read_bus() if os.path.exists(os.path.join(SRC, 'bus_stops.csv')) else []
gb = grid(bus)
for i in range(N):
    p, d = nearest(gb, lat[i], lng[i], 1000)
    if p:
        if not p[6]:
            # 다른 지역 BIS의 줄이면 30m 안의 같은 이름, 자기 지역 줄로 바꾼다(서울 정류장의 경기BIS 줄 등)
            q, dq = nearest(gb, p[1], p[2], 30, ok=lambda x: x[6] and x[0] == p[0])
            if q:
                p, d = q, dist(lat[i], lng[i], q[1], q[2])
        b = [p[0], int(round(d)), round(p[1] * 1e5), round(p[2] * 1e5), p[3], p[4], p[5]]
        while b and b[-1] == '':
            b.pop()
        info[i]['b'] = b
        stat['버스정류장'] += 1
        # 건너편 정류장(사용자 2026-11-28: 버스는 방향이 둘이다). 다른 번호, 같은 관리 지역 줄 가운데 그 정류장에서 5m 넘는 곳.
        #  같은 이름이면 300m 안, 이름 줄기가 같으면(앞, 건너, 맞은편, 출구 번호, 끝 숫자, 점 뒤를 뗀 이름) 150m 안에서 가장 가까운 곳.
        #  5m 안은 같은 자리를 두 번 올린 줄이라 뺀다.
        #  내리기만 하는 정류장(이름에 하차)은 짝으로 삼지 않는다.
        far = lambda x: x[3] != p[3] and '하차' not in x[0] and x[6] == p[6] and dist(p[1], p[2], x[1], x[2]) > 5
        q, dq = nearest(gb, p[1], p[2], 300, ok=lambda x: x[0] == p[0] and far(x))
        if not q and len(stem(p[0])) >= 2:
            q, dq = nearest(gb, p[1], p[2], 150, ok=lambda x: stem(x[0]) == stem(p[0]) and far(x))
        if q:
            b2 = [q[0], int(round(dist(lat[i], lng[i], q[1], q[2]))), round(q[1] * 1e5), round(q[2] * 1e5), q[3], q[4], q[5]]
            while b2 and b2[-1] == '':
                b2.pop()
            info[i]['b2'] = b2
            stat['건너편 정류장'] += 1
print('버스정류장', len(bus), '곳, 붙은 카페', stat['버스정류장'], '건너편까지', stat['건너편 정류장'], flush=True)

sub = read_subway()
if sub:
    gs = grid(sub)
    for i in range(N):
        p, d = nearest(gs, lat[i], lng[i], 1000)
        if p:
            info[i]['s'] = [p[0], int(round(d))]
            stat['지하철역'] += 1
    print('지하철역', len(sub), '곳, 붙은 카페', stat['지하철역'], flush=True)
else:
    print('지하철역 파일이 없어 건너뜀(작업/info_src/subway.csv 또는 subway.xlsx)', flush=True)

pk_path = os.path.join(SRC, 'parking.json')
if os.path.exists(pk_path):
    park = json.load(open(pk_path, encoding='utf-8'))
    gp = grid(park)
    for i in range(N):
        p, d = nearest(gp, lat[i], lng[i], 500)
        if p:
            fee = p[3] if p[3] in ('무료', '유료', '혼합') else ''
            x = dict(p[5]) if len(p) > 5 else {}
            x['y'], x['x'] = round(p[1] * 1e5), round(p[2] * 1e5)
            info[i]['p'] = [p[0], int(round(d)), fee, x]
            stat['주차장'] += 1
    print('주차장', len(park), '곳, 붙은 카페', stat['주차장'], flush=True)

mo_path = os.path.join(SRC, 'money.json')
if os.path.exists(mo_path):
    money = json.load(open(mo_path, encoding='utf-8'))
    for m in money:
        m.append(norm(m[0]))
    gm = grid(money)
    for i in range(N):
        n = norm(D['name'][i])
        p, d = nearest(gm, lat[i], lng[i], 150, ok=lambda q: similar(n, q[3]) >= 0.7)
        if p:
            info[i]['m'] = 1
            stat['지역화폐'] += 1
    print('지역화폐 가맹점', len(money), '곳, 붙은 카페', stat['지역화폐'], flush=True)

bld_path = os.path.join(SRC, 'bld.json')
if os.path.exists(bld_path):
    bld = json.load(open(bld_path, encoding='utf-8'))      # {이름표: [승강기, 사용승인 연도, 주차 대수]}
    for i in range(N):
        v = bld.get(cids[i])
        if not v:
            continue
        e, y, c = v
        if e:
            info[i]['e'] = e
        if y:
            info[i]['y'] = y
        if y and c is not None:      # 사용승인 연도가 빈 건물은 기록이 부실해서 주차 0대도 믿지 않는다
            info[i]['c'] = c
        stat['건축물대장'] += 1
    print('건축물대장 붙은 카페', stat['건축물대장'], flush=True)

# ---------- 쓰기 ----------
files = collections.defaultdict(dict)
for i in range(N):
    if info[i]:
        files[cids[i][:2]][cids[i]] = info[i]
os.makedirs(OUT, exist_ok=True)
for fn in os.listdir(OUT):
    if fn.endswith('.json') and fn[:-5] not in files:
        os.remove(os.path.join(OUT, fn))
total = 0
for k, v in files.items():
    path = os.path.join(OUT, k + '.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(v, f, ensure_ascii=False, separators=(',', ':'), sort_keys=True)
    total += os.path.getsize(path)
print('저장 info/', len(files), '개 파일', total // 1024, 'KB, 정보가 붙은 카페', sum(1 for x in info if x), '/', N, flush=True)
