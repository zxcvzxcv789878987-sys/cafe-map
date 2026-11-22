# 카페 목록(cafes_raw.csv)에 브랜드와 매장 면적을 붙여 cafes.js를 만든다.
# 사용법: python -I -X utf8 build.py <작업폴더> <출력 cafes.js> <인허가 CSV...>
import csv, sys, re, json, collections, difflib, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from brands import BRANDS

workdir, outpath, license_files = sys.argv[1], sys.argv[2], sys.argv[3:]
csv.field_size_limit(10**9)

SIDO = {
    '서울': '서울', '부산': '부산', '대구': '대구', '인천': '인천', '대전': '대전', '울산': '울산',
    '세종': '세종', '경기': '경기', '강원': '강원', '충청북': '충북', '충북': '충북',
    '충청남': '충남', '충남': '충남', '전라북': '전북', '전북': '전북', '경상북': '경북',
    '경북': '경북', '경상남': '경남', '경남': '경남', '제주': '제주',
    # 2026년 통합으로 상가정보는 '전남광주통합특별시', 인허가 자료는 옛 이름을 쓴다. 한 묶음으로 본다.
    '광주': '광전', '전라남': '광전', '전남': '광전',
}
NUM = re.compile(r'^(?:지하)?(\d+(?:-\d+)?),?$')


def sido_code(tok):
    for k, v in SIDO.items():
        if tok.startswith(k):
            return v
    return tok[:2]


def addr_key(addr):
    """도로명주소에서 '시도|시군구 도로명|건물번호'만 남긴다. 층, 호수, 괄호 안 동 이름은 버린다."""
    t = addr.replace('(', ' (').split()
    if len(t) < 3:
        return None
    for i in range(1, len(t) - 1):
        if t[i].endswith(('로', '길')):
            m = NUM.match(t[i + 1])
            if m:
                return sido_code(t[0]) + '|' + ' '.join(t[1:i + 1]) + '|' + m.group(1)
    return None


def norm(n):
    n = re.sub(r'\([^)]*\)', '', n)
    return re.sub(r'[^0-9a-z가-힣]', '', n.lower())


FILLER = re.compile(r'카페|커피|coffee|cafe|로스터스|로스터리|베이커리|디저트|점$')


def core(n):
    c = FILLER.sub('', n)
    return c if len(c) >= 2 else n


def brand_of(n):
    for i, (_, _, pats) in enumerate(BRANDS):
        if any(p in n for p in pats):
            return i
    return -1


def similar(a, b):
    """같은 가게 이름으로 볼 만한 정도(0~1)."""
    if not a or not b:
        return 0.0
    ca, cb = core(a), core(b)
    if len(ca) >= 2 and len(cb) >= 2 and (ca in cb or cb in ca):
        return 1.0
    return max(difflib.SequenceMatcher(None, a, b).ratio(),
               difflib.SequenceMatcher(None, ca, cb).ratio())


# 1. 인허가 자료를 주소별로 모은다. 영업 중인 곳만.
lic = collections.defaultdict(list)
lic_rows = 0
for path in license_files:
    with open(path, encoding='cp949', errors='replace', newline='') as f:
        r = csv.reader(f)
        h = next(r)
        ih = {k: i for i, k in enumerate(h)}
        i_state, i_name, i_addr = ih['영업상태명'], ih['사업장명'], ih['도로명주소']
        i_a1, i_a2 = ih.get('시설총규모'), ih.get('소재지면적')
        i_type = ih.get('업태구분명')
        for row in r:
            if len(row) != len(h) or '영업' not in row[i_state]:
                continue
            area = 0.0
            for i in (i_a1, i_a2):
                if i is None:
                    continue
                try:
                    area = max(area, float(row[i] or 0))
                except ValueError:
                    pass
            if area <= 0 or area > 30000:
                continue
            k = addr_key(row[i_addr])
            if not k:
                continue
            n = norm(row[i_name])
            lic[k].append((n, brand_of(n), area, row[i_type] if i_type is not None else ''))
            lic_rows += 1
print('인허가 영업 중', lic_rows, '주소', len(lic))

# 2. 카페마다 브랜드를 정하고, 같은 주소의 인허가 자료에서 이름이 가장 비슷한 곳의 면적을 가져온다.
CAFE_TYPES = ('커피숍', '다방', '기타 휴게음식점', '제과점영업', '까페', '전통찻집')
rows = list(csv.DictReader(open(os.path.join(workdir, 'cafes_raw.csv'), encoding='utf-8')))
names, lats, lngs, bidx, areas, regs, roads, floors = [], [], [], [], [], [], [], []
region_ix = {}
stat = collections.Counter()
for r in rows:
    raw = r['상호명'].strip()
    if not raw or raw == '업소명없음':
        continue
    branch = r['지점명'].strip()
    n = norm(raw)
    b = brand_of(raw.replace(' ', ''))
    area = 0.0
    k = addr_key(r['도로명주소'])
    cands = lic.get(k, []) if k else []
    if cands:
        full = norm(raw + branch)
        best, best_s = None, 0.0
        for cn, cb, ca, ct in cands:
            if b >= 0:
                s = 1.0 + similar(full, cn) if cb == b else 0.0
            else:
                s = similar(n, cn)
            if s > best_s:
                best, best_s = ca, s
        if best_s >= 0.6:
            area = best
            stat['이름으로 맞춤'] += 1
        else:
            # 그 주소에 카페류 인허가가 하나뿐이면 같은 곳으로 본다.
            only = [c for c in cands if c[3] in CAFE_TYPES]
            if len(only) == 1 and len(cands) <= 2 and b < 0 and only[0][1] < 0:
                area = only[0][2]
                stat['주소로 맞춤'] += 1
            else:
                stat['이름 불일치'] += 1
    else:
        stat['주소 없음'] += 1
    disp = raw if not branch or branch in raw else raw + ' ' + branch
    reg = (r['시도명'] + ' ' + r['시군구명']).strip()
    if reg not in region_ix:
        region_ix[reg] = len(region_ix)
    road = r['도로명주소']
    pre = r['시도명'] + ' ' + r['시군구명'] + ' '
    if road.startswith(pre):
        road = road[len(pre):]
    fl = r['층정보']
    names.append(disp)
    lats.append(round(float(r['위도']) * 1e5))
    lngs.append(round(float(r['경도']) * 1e5))
    bidx.append(b)
    areas.append(round(area))
    regs.append(region_ix[reg])
    roads.append(road)
    floors.append(-1 if fl.startswith('지') else int(fl) if fl.isdigit() else 0)

print(len(names), dict(stat))
got = [a for a in areas if a > 0]
print('면적 있음', len(got), '%.1f%%' % (100 * len(got) / len(names)))
for t in (100, 200, 330, 500, 1000):
    print(' ', t, '㎡ 이상', sum(1 for a in got if a >= t))

data = {
    'brands': [[n, g] for n, g, _ in BRANDS],
    'regions': list(region_ix),
    'name': names, 'lat': lats, 'lng': lngs, 'brand': bidx,
    'area': areas, 'region': regs, 'road': roads, 'floor': floors,
}
with open(outpath, 'w', encoding='utf-8') as o:
    o.write('window.CAFES=')
    json.dump(data, o, ensure_ascii=False, separators=(',', ':'))
    o.write(';')
print('저장', outpath, os.path.getsize(outpath))
