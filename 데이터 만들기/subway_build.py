# -*- coding: utf-8 -*-
"""지도에 찍는 지하철역 목록(subway.js)을 만든다(2026-11-28, 지하철을 버스처럼).

재료(공식 자료만):
  1) 전국도시철도역사정보 표준데이터(국가철도공단, 철도 데이터 포털 엑셀): 역 이름, 노선, 좌표. cafe_info.py와 같은 주소에서 받는다.
  2) 국토교통부 TAGO 지하철정보(공공데이터포털 15098554): 역 이름으로 찾아 노선별 역 번호(시간표를 물을 때 쓴다)를 붙인다.

결과 한 줄: [경도*1e5, 위도*1e5, 이름, [[노선 이름, 색, TAGO 역 번호, 서울 실시간 여부], ...]]
  환승역은 같은 이름이 800m 안에 있으면 한 역으로 묶는다(노선마다 좌표가 조금씩 다르다). 좌표는 노선들의 가운데.

쓰는 법: python subway_build.py  (키는 datago_key.txt, 엑셀은 작업/info_src/subway.xlsx, 없으면 받는다)
"""
import json, math, os, re, sys, time, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(HERE, '작업', 'info_src')
UA = 'Mozilla/5.0 (cafemap data build)'
sys.stdout.reconfigure(encoding='utf-8')

# 철도 이름(노선번호) → 사람들이 부르는 노선 이름. 표준데이터는 경부선, 경원선처럼 철도 이름으로 적혀 있다.
LINE_BY_NO = {
    'I1101': '1호선', 'I4101': '1호선', 'I4102': '1호선', 'I4401': '1호선',
    'I1103': '3호선', 'I4106': '3호선', 'I1104': '4호선', 'I4103': '4호선', 'I4104': '4호선',
    'S1102': '2호선', 'S1121': '2호선', 'S1122': '2호선', 'S1105': '5호선', 'S1106': '6호선', 'S1107': '7호선',
    'S1108': '8호선', 'S4108': '8호선', 'S1109': '9호선',
    'I4105': '수인분당선', 'I28K1': '수인분당선', 'I11D1': '신분당선', 'I4108': '경의중앙선', 'I41K2': '경춘선',
    'I41K5': '경강선', 'I41WS': '서해선', 'I28A1': '공항철도', 'L11SL': '신림선', 'L11UI': '우이신설선',
    'L41E1': '에버라인', 'L41G1': '김포골드라인', 'L41U1': '의정부경전철',
    'S2801': '인천1호선', 'S2802': '인천2호선', 'S28M1': '인천자기부상',
    'S2601': '부산1호선', 'S2602': '부산2호선', 'S2603': '부산3호선', 'L2604': '부산4호선', 'L48B1': '부산김해경전철', 'I26K6': '동해선',
    'S2701': '대구1호선', 'S2702': '대구2호선', 'S2703': '대구3호선', 'I27K7': '대경선',
    'S2901': '광주1호선', 'S3001': '대전1호선',
}
# 노선 색(각 운영기관이 노선도에 쓰는 색).
COLOR = {
    '1호선': '#0052A4', '2호선': '#00A84D', '3호선': '#EF7C1C', '4호선': '#00A5DE', '5호선': '#996CAC', '6호선': '#CD7C2F',
    '7호선': '#747F00', '8호선': '#E6186C', '9호선': '#BDB092', '수인분당선': '#F5A200', '신분당선': '#D4003B', '경의중앙선': '#77C4A3',
    '경춘선': '#0C8E72', '경강선': '#0054A6', '서해선': '#8FC31F', '공항철도': '#0090D2', '신림선': '#6789CA', '우이신설선': '#B0CE18',
    '에버라인': '#56AD2D', '김포골드라인': '#A17800', '의정부경전철': '#FDA600', '인천1호선': '#7CA8D5', '인천2호선': '#ED8B00',
    '인천자기부상': '#FFCD12', '부산1호선': '#F06A00', '부산2호선': '#81BF48', '부산3호선': '#BB8C00', '부산4호선': '#217DCB',
    '부산김해경전철': '#8652A1', '동해선': '#0066B3', '대구1호선': '#D93F5C', '대구2호선': '#00AA80', '대구3호선': '#FFB100',
    '대경선': '#3A8AC4', '광주1호선': '#009088', '대전1호선': '#007448',
}
# 서울 열린데이터광장 실시간 도착정보가 주는 노선(서울시 안의 역만). 그 밖은 시간표로 "예정"을 보여 준다.
SEOUL_RT = {'1호선', '2호선', '3호선', '4호선', '5호선', '6호선', '7호선', '8호선', '9호선', '수인분당선', '신분당선', '경의중앙선',
            '경춘선', '공항철도', '우이신설선', '서해선', '경강선', '신림선'}
# TAGO 역 번호 앞머리로 지역을 가른다(같은 이름의 역이 여러 도시에 있다: 시청, 중앙, 동대구 등).
REGION_PREFIX = {'부산': ('MTRBS', 'MTRBG', 'MTRKRK6'), '대구': ('MTRDG', 'MTRKRK7'), '광주': ('MTRGJ',), '대전': ('MTRDJ',)}


def region_of(line):
    for r in ('부산', '대구', '광주', '대전'):
        if line.startswith(r):
            return r
    if line == '동해선':
        return '부산'
    if line == '대경선':
        return '대구'
    return '수도권'


def short(n):
    """괄호(부역명)와 끝의 '역'을 뗀 이름. 표준데이터는 철도공사 역에 '연천역'처럼 '역'이 붙어 있고 TAGO는 '서울역'만 붙어 있다."""
    n = re.sub(r'\(.*?\)', '', n).strip()
    return n[:-1] if len(n) > 2 and n.endswith('역') else n


def show_name(n):
    """지도와 창에 쓰는 이름. 서울역만 '역'을 붙인다(그냥 '서울'은 어색하다)."""
    n = short(n)
    return '서울역' if n == '서울' else n


def norm_line(t):
    """노선 이름을 견주기 쉽게: 공백, '선', '도시철도', '지하철', '경전철' 같은 말을 뗀다."""
    t = re.sub(r'\s', '', t or '')
    for w in ('도시철도', '지하철', '광역철도', '경량'):
        t = t.replace(w, '')
    return t.replace('호선', '').replace('선', '').replace('라인', '')


def read_rows():
    p = os.path.join(SRC, 'subway.xlsx')
    if not os.path.exists(p):
        os.makedirs(SRC, exist_ok=True)
        req = urllib.request.Request('https://data.kric.go.kr/rips/dataset/download.file?type=filedata&id=32&operation=1',
                                     headers={'User-Agent': UA, 'Referer': 'https://data.kric.go.kr/rips/M_01_01/detail.do?id=32'})
        data = urllib.request.urlopen(req, timeout=120).read()
        if data[:2] != b'PK':
            raise RuntimeError('지하철역 파일이 엑셀이 아니다.')
        open(p, 'wb').write(data)
    import openpyxl
    ws = openpyxl.load_workbook(p, read_only=True, data_only=True).active
    rows = [[('' if c is None else str(c)) for c in r] for r in ws.iter_rows(values_only=True)]
    h = rows[0]
    ix = {k: h.index(k) for k in ('역사명', '노선번호', '노선명', '역위도', '역경도', '운영기관명')}
    out, skip = [], {}
    for r in rows[1:]:
        no = r[ix['노선번호']].strip()
        line = LINE_BY_NO.get(no)
        if not line:
            skip[no + ' ' + r[ix['노선명']]] = skip.get(no + ' ' + r[ix['노선명']], 0) + 1
            continue
        try:
            la, lo = float(r[ix['역위도']]), float(r[ix['역경도']])
        except ValueError:
            continue
        out.append({'name': r[ix['역사명']].strip(), 'line': line, 'la': la, 'lo': lo})
    if skip:
        print('노선 이름을 모르는 줄(빠짐):', skip)
    return out


def dist(a, b, c, d):
    k = math.cos(math.radians((a + c) / 2))
    return math.hypot((a - c) * 111320, (b - d) * 111320 * k)


TAGO = 'https://apis.data.go.kr/1613000/SubwayInfo/GetKwrdFndSubwaySttnList'


def tago_search(key, name, cache):
    if name in cache:
        return cache[name]
    url = TAGO + '?serviceKey=' + key + '&_type=json&numOfRows=100&subwayStationName=' + urllib.parse.quote(name)
    for t in range(3):
        try:
            d = json.load(urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': UA}), timeout=30))
            it = (d['response']['body'].get('items') or {}) or {}
            it = it.get('item', []) if isinstance(it, dict) else []
            if isinstance(it, dict):
                it = [it]
            cache[name] = it
            return it
        except Exception as e:  # 잠깐 실패하면 다시
            err = e
            time.sleep(1 + t)
    raise RuntimeError('TAGO 실패 %s: %s' % (name, err))


# TAGO 노선 이름이 표준데이터와 다르게 적힌 것(TAGO 이름 → 우리 노선 이름 후보).
TAGO_ALIAS = {'자기부상': '인천자기부상', '동해': '동해선','공항': '공항철도', '수인분당': '수인분당선', '신분당': '신분당선', '김포골드라인': '김포골드라인', '에버라인': '에버라인',
              '의정부': '의정부경전철', '우이신설': '우이신설선', '신림': '신림선', '경의중앙': '경의중앙선', '경춘': '경춘선', '경강': '경강선', '서해': '서해선'}


def tago_line_ok(tago_name, tago_id, line):
    """TAGO 한 줄이 우리 노선과 같은지. 지역 앞머리부터 보고, 이름을 견준다."""
    reg = region_of(line)
    if reg != '수도권':
        if not tago_id.startswith(REGION_PREFIX[reg]):
            return False
        num = re.sub(r'\D', '', line)
        if line in ('동해선', '대경선', '부산김해경전철'):
            return norm_line(tago_name) in norm_line(line) or norm_line(line) in norm_line(tago_name)
        return re.sub(r'\D', '', tago_name) == num
    if any(tago_id.startswith(p) for ps in REGION_PREFIX.values() for p in ps):
        return False
    a, b = norm_line(TAGO_ALIAS.get(tago_name, tago_name)), norm_line(line)
    return a == b


def main():
    key = open(os.path.join(HERE, 'datago_key.txt'), encoding='utf-8').read().strip()
    rows = read_rows()
    print('표준데이터 줄', len(rows))
    cache_p = os.path.join(SRC, 'tago_subway_cache.json')
    cache = json.load(open(cache_p, encoding='utf-8')) if os.path.exists(cache_p) else {}
    miss = []
    for k, r in enumerate(rows):
        cands = []
        # 가운뎃점이 든 이름(시청·용인대)은 TAGO에 점(.)으로 적혀 있어 앞마디로 찾고, 견줄 때는 점들을 뗀다.
        same = lambda a, b: re.sub(r'[·.\s]', '', short(a)) == re.sub(r'[·.\s]', '', short(b))
        for q in dict.fromkeys([short(r['name']), re.sub(r'\(.*?\)', '', r['name']).strip(), re.split(r'[·.]', short(r['name']))[0]]):
            cands += [c for c in tago_search(key, q, cache) if same(c['subwayStationName'], r['name'])]
        cands = list({c['subwayStationId']: c for c in cands}.values())
        ok = [c for c in cands if tago_line_ok(c['subwayRouteName'], c['subwayStationId'], r['line'])]
        # 철도 이름 하나에 노선이 둘인 곳: 경원선 용산~망우(이촌, 옥수, 왕십리 등)는 경의중앙선이 다니고,
        #  표준데이터의 경의중앙선 번호에 든 광운대는 경춘선이 다닌다. 원래 노선이 TAGO에 없으면 이 순서로 바꿔 본다.
        for alt in ({'1호선': ['경의중앙선'], '경의중앙선': ['경춘선']}.get(r['line'], []) if not ok else []):
            ok = [c for c in cands if tago_line_ok(c['subwayRouteName'], c['subwayStationId'], alt)]
            if ok:
                r['line'] = alt
                break
        # 같은 노선에 번호가 둘(지선 등)이면 다 둔다.
        r['ids'] = sorted(set(c['subwayStationId'] for c in ok))
        if not r['ids']:
            miss.append((r['name'], r['line'], [(c['subwayStationId'], c['subwayRouteName']) for c in cands]))
        if k % 100 == 0:
            json.dump(cache, open(cache_p, 'w', encoding='utf-8'), ensure_ascii=False)
    json.dump(cache, open(cache_p, 'w', encoding='utf-8'), ensure_ascii=False)
    print('TAGO 번호를 못 붙인 줄', len(miss))
    for m in miss:
        print('  ', m)
    # 같은 이름 800m 안은 한 역으로.
    groups = []
    for r in rows:
        nm = show_name(r['name'])
        g = next((g for g in groups if g['name'] == nm and dist(g['la'], g['lo'], r['la'], r['lo']) < 800), None)
        if not g:
            g = {'name': nm, 'la': r['la'], 'lo': r['lo'], 'rows': []}
            groups.append(g)
        g['rows'].append(r)
        g['la'] = sum(x['la'] for x in g['rows']) / len(g['rows'])
        g['lo'] = sum(x['lo'] for x in g['rows']) / len(g['rows'])
    order = list(COLOR)
    out = []
    for g in groups:
        lines = {}
        for r in g['rows']:
            L = lines.setdefault(r['line'], [r['line'], COLOR[r['line']], [], 1 if r['line'] in SEOUL_RT else 0])
            L[2] = sorted(set(L[2]) | set(r['ids']))
        ls = sorted(lines.values(), key=lambda L: order.index(L[0]))
        for L in ls:
            L[2] = ','.join(L[2])
        out.append([round(g['lo'] * 1e5), round(g['la'] * 1e5), g['name'], ls])
    out.sort(key=lambda s: (s[1], s[0]))
    js = '// 지하철역(데이터 만들기/subway_build.py가 만듦). [경도*1e5, 위도*1e5, 이름, [[노선, 색, TAGO 역 번호, 서울 실시간]]]\nwindow.SUBWAY=' + \
         json.dumps(out, ensure_ascii=False, separators=(',', ':')) + ';\n'
    open(os.path.join(ROOT, 'subway.js'), 'w', encoding='utf-8').write(js)
    print('역', len(out), '곳, subway.js', len(js.encode('utf-8')) // 1024, 'KB')


if __name__ == '__main__':
    main()
