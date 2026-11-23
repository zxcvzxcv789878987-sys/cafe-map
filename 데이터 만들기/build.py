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
        # ^로 시작하는 글자는 이름의 맨 앞에 있을 때만 맞는 것으로 본다.
        if any(n.startswith(p[1:]) if p[0] == '^' else p in n for p in pats):
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
# 주소별로 영업 중인 곳과 폐업 신고된 곳의 이름. 면적이 없는 줄도 다 모은다. 문 닫은 카페를 가려내는 데 쓴다.
open_names, closed_names = collections.defaultdict(list), collections.defaultdict(list)
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
            if len(row) != len(h):
                continue
            k = addr_key(row[i_addr])
            if not k:
                continue
            n = norm(row[i_name])
            if '폐업' in row[i_state]:
                closed_names[k].append(n)
            if '영업' not in row[i_state]:
                continue
            open_names[k].append(n)
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
            lic[k].append((n, brand_of(n), area, row[i_type] if i_type is not None else ''))
            lic_rows += 1
print('인허가 영업 중', lic_rows, '주소', len(lic))

# 2. 카페마다 브랜드를 정하고, 같은 주소의 인허가 자료에서 이름이 가장 비슷한 곳의 면적을 가져온다.
CAFE_TYPES = ('커피숍', '다방', '기타 휴게음식점', '제과점영업', '까페', '전통찻집')
rows = list(csv.DictReader(open(os.path.join(workdir, 'cafes_raw.csv'), encoding='utf-8')))
names, lats, lngs, bidx, areas, dongs, roads, floors = [], [], [], [], [], [], [], []
closed = []      # 인허가 자료에서 같은 주소, 비슷한 이름이 폐업으로만 나오는 카페
# 지역은 시도 > 시군구 > 행정동 세 단계로 번호를 매긴다.
sido_ix, sgg_ix, dong_ix = {}, {}, {}
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
    gone = False
    if k and k in closed_names:
        full_n = norm(raw + branch)
        gone = (any(similar(full_n, cn) >= 0.6 for cn in closed_names[k])
                and not any(similar(full_n, cn) >= 0.6 for cn in open_names.get(k, ())))
    closed.append(gone)
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
    sido, sgg, dong = r['시도명'].strip(), r['시군구명'].strip() or r['시도명'].strip(), r['행정동명'].strip() or '기타'
    si = sido_ix.setdefault(sido, len(sido_ix))
    gi = sgg_ix.setdefault((si, sgg), len(sgg_ix))
    di = dong_ix.setdefault((gi, dong), len(dong_ix))
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
    dongs.append(di)
    roads.append(road)
    floors.append(-1 if fl.startswith('지') else int(fl) if fl.isdigit() else 0)

# 3. 좌표를 카카오에서 받은 실제 매장 좌표로 바꾼다.
#    공공데이터 좌표는 건물 주소의 좌표라서 같은 건물의 카페가 한 점에 포개지고, 실제 매장 자리와도 어긋난다.
#    kakao_all.py가 받아 둔 전국 카페 목록과 짝을 짓고, 못 찾은 곳은 kakao_kw.py가 이름으로 물어 둔 답에서 찾는다.
here = os.path.dirname(os.path.abspath(__file__))
places_path = os.path.join(here, 'kakao_places.json')
in_kakao = [0] * len(names)
# 카카오 운영정책은 로컬 API로 받은 좌표를 저장해 두고 쓰거나 공개하는 것을 금지한다(장소 번호와 주소는 저장해도 된다).
# 그래서 파일을 둘로 만든다. 인터넷에 올리는 cafes.js는 공공데이터 좌표, 내 컴퓨터에서만 쓰는 cafes.local.js는 카카오 좌표.
pub_lats, pub_lngs = lats[:], lngs[:]
kid = [0] * len(names)        # 카카오 장소 번호. 카페 카드에서 카카오맵의 그 가게 화면을 바로 띄우는 데 쓴다.
drop = set()
if os.path.exists(places_path):
    import kakao_match
    places = json.load(open(places_path, encoding='utf-8'))['places']
    out, dups, kstat = kakao_match.match(names, lats, lngs, bidx, roads, places)
    new_xy = {i: (places[pid][4], places[pid][3]) for i, pid in out.items()}
    for i, pid in out.items():
        kid[i] = int(pid)
    taken = set(out.values())
    kw_path = os.path.join(here, 'kakao_kw.json')
    kw = json.load(open(kw_path, encoding='utf-8')) if os.path.exists(kw_path) else {}
    left = []                                 # 아직 이름으로 물어보지 않은 곳. kakao_kw.py가 읽는다.
    for i in range(len(names)):
        if i in out or i in dups:
            continue
        docs = kw.get('%s@%d,%d' % (names[i], lats[i], lngs[i]))
        if docs is None:
            left.append([names[i], lats[i], lngs[i]])
            kstat['아직 이름으로 안 물어봄'] += 1
            continue
        hit = kakao_match.pick_by_name(names[i], bidx[i], docs, taken)
        if hit:
            taken.add(hit[0])
            new_xy[i] = (hit[2], hit[1])
            kid[i] = int(hit[0])
            kstat['이름으로 물어서 찾음'] += 1
        else:
            kstat['카카오에 없음'] += 1
    json.dump(left, open(os.path.join(here, 'kakao_left.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    for i, (la, ln) in new_xy.items():
        lats[i], lngs[i] = round(la * 1e5), round(ln * 1e5)
        in_kakao[i] = 1
    # 공공데이터에 같은 가게가 두 줄로 들어 있으면 한 줄만 남긴다. 면적은 둘 중 있는 쪽 것을 쓴다.
    for i, i2 in dups.items():
        areas[i2] = max(areas[i2], areas[i])
        drop.add(i)
    # 카카오 지도에도 없고 인허가 자료에서도 폐업 신고된 카페는 뺀다(서로 다른 두 자료가 같은 말을 하는 경우만).
    gone_n = 0
    for i in range(len(names)):
        if closed[i] and not in_kakao[i] and i not in drop:
            drop.add(i)
            gone_n += 1
    print('카카오에 없고 폐업 신고된 카페(뺌)', gone_n)
    print('카카오 좌표', dict(kstat))
    print('카카오 좌표로 바꾼 카페', len(new_xy), '두 줄이라 한 줄로 합친 카페', len(dups))
if drop:
    keep = [i for i in range(len(names)) if i not in drop]
    names, lats, lngs, bidx, areas, dongs, roads, floors, in_kakao, kid, pub_lats, pub_lngs = (
        [arr[i] for i in keep] for arr in (names, lats, lngs, bidx, areas, dongs, roads, floors, in_kakao, kid, pub_lats, pub_lngs))
print(len(names), dict(stat))
got = [a for a in areas if a > 0]
print('면적 있음', len(got), '%.1f%%' % (100 * len(got) / len(names)))
for t in (100, 200, 330, 500, 1000):
    print(' ', t, '㎡ 이상', sum(1 for a in got if a >= t))

data = {
    'brands': [[n, g] for n, g, _ in BRANDS],
    'sido': list(sido_ix),
    'sgg': [[n, si] for (si, n) in sgg_ix],
    'dong': [[n, gi] for (gi, n) in dong_ix],
    'name': names, 'lat': lats, 'lng': lngs, 'brand': bidx,
    'area': areas, 'dongOf': dongs, 'road': roads, 'floor': floors,
    'kid': kid,
    'kakao': in_kakao,          # 1: 카카오 지도에서 확인된 카페(좌표도 카카오 것), 0: 카카오에 없어서 공공데이터 좌표 그대로
}
def write(path, d):
    with open(path, 'w', encoding='utf-8') as o:
        o.write('window.CAFES=')
        json.dump(d, o, ensure_ascii=False, separators=(',', ':'))
        o.write(';')
    print('저장', path, os.path.getsize(path))


local = dict(data)
data['lat'], data['lng'] = pub_lats, pub_lngs
del data['kakao']
write(outpath, data)                                    # 공개용: 공공데이터 좌표
if os.path.exists(places_path):
    write(outpath[:-3] + '.local.js', local)            # 내 컴퓨터용: 카카오 좌표
