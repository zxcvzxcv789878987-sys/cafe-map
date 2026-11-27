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
# 주소별 영업 중인 인허가 전부(넓이가 없는 줄도). 문 연 달(인허가일자)을 붙이고, 카페 목록에 아직 없는 최근 개업 카페를 찾는 데 쓴다.
# [이름(다듬은 것), 브랜드, 인허가 연월(YYYYMM), 업태, 넓이, 원래 이름, 도로명주소, 일반음식점 자료인가]
lic_all = collections.defaultdict(list)
# 주소별 폐업한 인허가의 [이름, 브랜드, 인허가 연월]. 같은 자리에서 같은 이름으로 허가를 새로 받은 가게(주인이나 법인이 바뀐 경우)를 알아보는 데 쓴다.
closed_all = collections.defaultdict(list)


def ym_of(d):
    d = re.sub(r'[^0-9]', '', d)
    return int(d[:6]) if len(d) >= 6 and '1900' <= d[:4] <= '2100' and '01' <= d[4:6] <= '12' else 0


lic_rows = 0
for path in license_files:
    is_general = 'general' in os.path.basename(path)
    with open(path, encoding='cp949', errors='replace', newline='') as f:
        r = csv.reader(f)
        h = next(r)
        ih = {k: i for i, k in enumerate(h)}
        i_state, i_name, i_addr = ih['영업상태명'], ih['사업장명'], ih['도로명주소']
        i_a1, i_a2 = ih.get('시설총규모'), ih.get('소재지면적')
        i_type = ih.get('업태구분명')
        i_date = ih.get('인허가일자')
        i_x, i_y = ih.get('좌표정보(X)'), ih.get('좌표정보(Y)')
        for row in r:
            if len(row) != len(h):
                continue
            k = addr_key(row[i_addr])
            if not k:
                continue
            n = norm(row[i_name])
            if '폐업' in row[i_state]:
                closed_names[k].append(n)
                closed_all[k].append((n, brand_of(n), ym_of(row[i_date]) if i_date is not None else 0))
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
            try:
                tx, ty = float(row[i_x]), float(row[i_y])
            except (TypeError, ValueError, IndexError):
                tx = ty = None
            lic_all[k].append([n, brand_of(n), ym_of(row[i_date]) if i_date is not None else 0, row[i_type] if i_type is not None else '',
                               area if 0 < area <= 30000 else 0.0, row[i_name].strip(), row[i_addr], is_general, tx, ty])
            if area <= 0 or area > 30000:
                continue
            lic[k].append((n, brand_of(n), area, row[i_type] if i_type is not None else ''))
            lic_rows += 1
print('인허가 영업 중', lic_rows, '주소', len(lic))

# 2. 카페마다 브랜드를 정하고, 같은 주소의 인허가 자료에서 이름이 가장 비슷한 곳의 면적을 가져온다.
CAFE_TYPES = ('커피숍', '다방', '기타 휴게음식점', '제과점영업', '까페', '전통찻집')
rows = list(csv.DictReader(open(os.path.join(workdir, 'cafes_raw.csv'), encoding='utf-8')))
# 업종이 빵/도넛인 가게도 넣어 보고, 카카오맵이 카페로 분류한 곳만 남긴다(3번 뒤). 대부분은 빵만 파는 빵집이라 빠진다(사용자 결정 2026-11-26).
bread_path = os.path.join(workdir, 'bread_raw.csv')
bread_rows = list(csv.DictReader(open(bread_path, encoding='utf-8'))) if os.path.exists(bread_path) else []
for r in bread_rows:
    r['_bread'] = 1
rows += bread_rows
bread = set()      # 빵/도넛에서 온 줄의 번호
names, lats, lngs, bidx, areas, dongs, roads, floors = [], [], [], [], [], [], [], []
closed = []      # 인허가 자료에서 같은 주소, 비슷한 이름이 폐업으로만 나오는 카페
since = []       # 문 연 달(인허가일자의 연월, YYYYMM). 인허가 자료에서 같은 주소, 같은 이름을 찾은 카페만. 모르면 0.
used = set()     # 카페와 짝지어진 인허가 줄 (주소, 그 주소 안 순번)
at_addr = collections.defaultdict(list)   # 주소별로, 카페 목록에 있는 카페가 인허가와 짝이 지어졌는가
ltypes = []      # 넓이를 가져온 인허가의 업태(한식, 커피숍 등). 이름으로 맞춘 경우만 적는다.
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
    ltype = ''
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
        best, best_s, best_t = None, 0.0, ''
        for cn, cb, ca, ct in cands:
            if b >= 0:
                s = 1.0 + similar(full, cn) if cb == b else 0.0
            else:
                s = similar(n, cn)
            if s > best_s:
                best, best_s, best_t = ca, s, ct
        if best_s >= 0.6:
            ltype = best_t
            # 예식장 뷔페로 허가받은 곳의 넓이는 예식장 전체 넓이라서 카페 넓이로 쓰지 않는다.
            area = 0.0 if best_t == '뷔페식' else best
            stat['이름으로 맞춤'] += 1
        else:
            # 그 주소에 카페류 인허가가 하나뿐이면 같은 곳으로 본다.
            only = [c for c in cands if c[3] in CAFE_TYPES]
            if len(only) == 1 and len(cands) <= 2 and b < 0 and only[0][1] < 0:
                # 이름이 다른 가게의 넓이를 빌려 오는 것이라서, 100평이 넘는 큰 넓이는 믿지 않는다(대형카페에 엉뚱한 곳이 끼지 않게).
                area = only[0][2] if only[0][2] < 330 else 0.0
                stat['주소로 맞춤'] += 1
            else:
                stat['이름 불일치'] += 1
    else:
        stat['주소 없음'] += 1
    # 문 연 달: 같은 주소의 영업 중 인허가 가운데 이름이 같은 곳의 인허가일자. 이름이 다르면 붙이지 않는다(남의 날짜를 빌려 오지 않는다).
    ym = 0
    if k and k in lic_all:
        full = norm(raw + branch)
        bj, bs = -1, 0.0
        for j, c in enumerate(lic_all[k]):
            if b >= 0:
                s = 1.0 + similar(full, c[0]) if c[1] == b else 0.0
            else:
                s = similar(n, c[0])
            if s > bs:
                bj, bs = j, s
        if bs >= 0.6:
            ym = lic_all[k][bj][2]
            if not r.get('_bread'):
                used.add((k, bj))      # 빵/도넛 줄은 인허가 줄을 차지하지 않는다(최근 개업 카페를 더할 때 막지 않게)
            # 오래된 가게가 새 카페로 나오지 않게 한다. 주인이나 법인이 바뀌면 허가를 새로 받아서 인허가일자가 최근으로 찍힌다.
            # (1) 같은 주소에 같은 이름(브랜드 매장은 같은 브랜드)의 폐업한 인허가가 있으면 그 가게가 이어진 것이다. 가장 이른 날짜를 문 연 달로 쓴다.
            for cn, cb, cy in closed_all.get(k, ()):
                if cy and cy < ym and ((b >= 0 and cb == b) or (b < 0 and similar(n, cn) >= 0.6)):
                    ym = cy
                    stat['허가를 새로 받은 가게(옛 날짜로 고침)'] += 1
            # (2) 상가정보에 등록된 달(상가업소번호에 들어 있다)이 인허가보다 석 달 넘게 이르면, 허가받기 전부터 있던 가게다.
            #     언제 열었는지는 알 수 없으므로 문 연 달을 비워 둔다(틀린 날짜를 적지 않는다).
            reg = ym_of(r['상가업소번호'][6:14]) if r.get('상가업소번호') else 0
            if ym and reg and (ym // 100 * 12 + ym % 100) - (reg // 100 * 12 + reg % 100) > 3:
                ym = 0
                stat['허가보다 먼저 등록된 가게(문 연 달 비움)'] += 1
    if k and not r.get('_bread'):
        at_addr[k].append(bs >= 0.6 if k in lic_all else False)
    since.append(ym)
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
    if r.get('_bread'):
        bread.add(len(names))
    names.append(disp)
    ltypes.append(ltype)
    lats.append(round(float(r['위도']) * 1e5))
    lngs.append(round(float(r['경도']) * 1e5))
    bidx.append(b)
    areas.append(round(area))
    dongs.append(di)
    roads.append(road)
    floors.append(-1 if fl.startswith('지') else int(fl) if fl.isdigit() else 0)

# 2-1. 카페 목록(상가정보)은 석 달에 한 번 나와서 최근에 문 연 카페가 빠져 있다. 인허가 자료에서 최근 열두 달 사이에 허가받은 카페를 더한다.
#   - 업태가 커피숍, 전통찻집이거나, 이름으로 브랜드를 알아본 곳이거나, 휴게음식점(일반음식점은 업태가 까페인 곳) 가운데 이름에 카페, 커피가 든 곳만.
#   - 인허가 자료에는 행정동과 위경도가 없다. 상가정보에 같은 건물(도로명주소)이 있을 때만 그 건물의 행정동과 좌표를 붙여서 더한다. 없으면 더하지 않는다.
#   - 그 주소에 인허가와 짝을 못 지은 카페가 이미 있으면 같은 가게일 수 있으므로 더하지 않는다(두 번 찍히지 않게).
NEW_TYPES = ('커피숍', '전통찻집')
NEW_WORD = re.compile(r'카페|까페|커피|coffee|cafe', re.I)
NOT_NEW = re.compile(r'호프|포차|부동산|공인중개|당구|노래|pc방|피씨방|편의점|만화카페|키즈카페|보드게임|보드카페|스터디카페|독서실|웨딩|뷔페|학원|네일|식당|다방|주점|술|pc\s*\)?\s*(?:카페|cafe|방)|피씨\s*(?:\(pc\))?\s*(?:카페|방)|스터디|만화|키즈|보드|룸카페|사주|타로|휴게실', re.I)
FLOOR = re.compile(r'(지하)?\s*(\d+)\s*층')
bpath = os.path.join(workdir, 'buildings.csv')
added = collections.Counter()
if os.path.exists(bpath):
    latest = max((c[2] for v in lic_all.values() for c in v), default=0)
    cut = (latest // 100 - 1) * 100 + latest % 100          # 열두 달 전
    want = collections.defaultdict(list)
    for k, v in lic_all.items():
        for j, c in enumerate(v):
            if c[2] < cut or (k, j) in used:
                continue
            nm = c[5]
            if NOT_NEW.search(nm):
                continue
            if any((c[1] >= 0 and cb == c[1]) or (c[1] < 0 and similar(c[0], cn) >= 0.6) for cn, cb, cy in closed_all.get(k, ())):
                added['같은 자리에서 허가를 새로 받은 가게라 넣지 않음'] += 1
                continue
            ok = (not c[7] and (c[3] in NEW_TYPES or c[1] >= 0)) or (NEW_WORD.search(nm) and (c[3] == '까페' if c[7] else c[3] in ('기타 휴게음식점', '떡카페', '아이스크림', '제과점영업')))
            if ok:
                want[k].append(c)
    bld = {}
    with open(bpath, encoding='utf-8', newline='') as f:
        r2 = csv.reader(f)
        next(r2)
        for row in r2:
            k = addr_key(row[0])
            if k in want and k not in bld:
                bld[k] = row
    for k, v in want.items():
        if k not in bld:
            added['건물을 못 찾아 넣지 않음'] += len(v)
            continue
        if not all(at_addr.get(k, [])):
            added['같은 주소에 짝 없는 카페가 있어 넣지 않음'] += len(v)
            continue
        got = []
        for c in v:
            if any(similar(c[0], g[0]) >= 0.6 for g in got):
                added['같은 가게가 두 줄'] += 1
                continue
            got.append(c)
            row = bld[k]
            sido, sgg, dong = row[1], row[2] or row[1], row[3] or '기타'
            si = sido_ix.setdefault(sido, len(sido_ix))
            gi = sgg_ix.setdefault((si, sgg), len(sgg_ix))
            di = dong_ix.setdefault((gi, dong), len(dong_ix))
            road = row[0]
            pre = row[1] + ' ' + row[2] + ' '
            if road.startswith(pre):
                road = road[len(pre):]
            m = FLOOR.search(c[6])
            names.append(c[5]); ltypes.append(c[3]); closed.append(False); since.append(c[2])
            lats.append(round(float(row[5]) * 1e5)); lngs.append(round(float(row[4]) * 1e5))
            bidx.append(brand_of(c[5].replace(' ', ''))); areas.append(0 if c[3] == '뷔페식' else round(c[4]))
            dongs.append(di); roads.append(road)
            floors.append(0 if not m else -1 if m.group(1) else int(m.group(2)))
            added['넣음'] += 1
    print('최근 열두 달(%d 이후) 인허가에서 더한 카페' % cut, dict(added))
print('문 연 달을 아는 카페', sum(1 for y in since if y), '/', len(since))

# 3. 좌표를 카카오에서 받은 실제 매장 좌표로 바꾼다.
#    공공데이터 좌표는 건물 주소의 좌표라서 같은 건물의 카페가 한 점에 포개지고, 실제 매장 자리와도 어긋난다.
#    kakao_all.py가 받아 둔 전국 카페 목록과 짝을 짓고, 못 찾은 곳은 kakao_kw.py가 이름으로 물어 둔 답에서 찾는다.
here = os.path.dirname(os.path.abspath(__file__))
places_path = os.path.join(here, 'kakao_places.json')
in_kakao = [0] * len(names)
kcat = [None] * len(names)     # 카카오가 그 장소를 어떤 종류로 분류했는가(카카오에 없으면 None)
# 카카오 운영정책은 로컬 API로 받은 좌표를 저장해 두고 쓰거나 공개하는 것을 금지한다(장소 번호와 주소는 저장해도 된다).
# 그래서 파일을 둘로 만든다. 인터넷에 올리는 cafes.js는 공공데이터 좌표, 내 컴퓨터에서만 쓰는 cafes.local.js는 카카오 좌표.
pub_lats, pub_lngs = lats[:], lngs[:]
kid = [0] * len(names)        # 카카오 장소 번호. 카페 카드에서 카카오맵의 그 가게 화면을 바로 띄우는 데 쓴다.
drop = set()
if os.path.exists(places_path):
    import kakao_match
    places = json.load(open(places_path, encoding='utf-8'))['places']
    # 카페 줄이 먼저 카카오 장소와 짝을 짓는다. 빵/도넛 줄은 그다음, 아무 카페 줄과도 짝지어지지 않은 카카오 장소하고만 짝을 짓는다.
    # (빵/도넛 줄이 카페 줄의 짝을 빼앗아 멀쩡한 카페가 빠지거나 이름이 바뀌던 것을 막는다. 같은 가게가 두 업종으로 올라 있으면 빵/도넛 줄은 짝이 없어 빠진다.)
    cafe_ix = [i for i in range(len(names)) if i not in bread]
    pick = lambda arr, ix: [arr[i] for i in ix]
    o1, d1, kstat, a1 = kakao_match.match(pick(names, cafe_ix), pick(lats, cafe_ix), pick(lngs, cafe_ix), pick(bidx, cafe_ix), pick(roads, cafe_ix), places)
    out = {cafe_ix[i]: pid for i, pid in o1.items()}
    dups = {cafe_ix[i]: cafe_ix[j] for i, j in d1.items()}
    addr_matched = set(cafe_ix[i] for i in a1)
    bread_ix = sorted(bread)
    if bread_ix:
        taken0 = set(out.values())
        rest = {pid: v for pid, v in places.items() if pid not in taken0}
        o2, d2, _s2, a2 = kakao_match.match(pick(names, bread_ix), pick(lats, bread_ix), pick(lngs, bread_ix), pick(bidx, bread_ix), pick(roads, bread_ix), rest)
        for i, pid in o2.items():
            out[bread_ix[i]] = pid
        for i, j in d2.items():
            dups[bread_ix[i]] = bread_ix[j]
        addr_matched |= set(bread_ix[i] for i in a2)
    new_xy = {i: (places[pid][4], places[pid][3]) for i, pid in out.items()}
    for i, pid in out.items():
        kid[i] = int(pid)
        kcat[i] = places[pid][5]
    taken = set(out.values())
    kw_path = os.path.join(here, 'kakao_kw.json')
    kw = json.load(open(kw_path, encoding='utf-8')) if os.path.exists(kw_path) else {}
    left = []                                 # 아직 이름으로 물어보지 않은 곳. kakao_kw.py가 읽는다.
    for i in range(len(names)):
        if i in out or i in dups:
            continue
        if i in bread:
            continue      # 빵/도넛 가게는 카카오의 전국 카페 목록에 있을 때만 쓴다. 이름으로 따로 묻지 않는다.
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
            kcat[i] = hit[3]
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
    # 빵/도넛 가게: 카카오맵이 카페(음식점 > 카페 ...)로 분류하고 이름까지 맞는 곳만 남긴다. 나머지는 뺀다.
    bread_keep = 0
    for i in bread:
        k = kcat[i]
        if i not in drop and k and k.startswith('음식점 > 카페') and i not in addr_matched and not re.search(r'사주카페|라이브카페|보드카페|만화방', k):
            bread_keep += 1
        else:
            drop.add(i)
    print('빵/도넛 가게', len(bread), '그중 카카오가 카페로 보는 곳(넣음)', bread_keep)
    # 카페가 아닌데 카페로 들어와 있는 곳을 뺀다. 공공데이터의 업종 분류가 틀린 경우다.
    #  1) 카카오에 있는 곳은 카카오의 분류를 믿는다. 카페(커피, 디저트, 찻집 등), 제과점, 간식 가게만 남긴다.
    #     키즈카페, 보드카페, 만화카페, 사주카페, 라이브카페처럼 이름만 카페인 곳과 한식, 술집, 꽃집 같은 곳은 뺀다.
    #  2) 카카오에 없는 곳은 인허가 업태가 한식, 뷔페식, 호프처럼 카페가 아니거나, 이름에 웨딩, PC방 같은 말이 들어 있으면 뺀다.
    #  이름으로 브랜드를 알아본 곳(스타벅스 등)은 그대로 둔다.
    #  이름에 카페, 커피 같은 말이 들어 있으면 다른 자료가 음식점이라고 해도 남긴다(일반음식점으로 허가받은 카페가 많다).
    OK_KAKAO = re.compile(r'음식점 > 카페|제과,베이커리|음식점 > 간식')
    NOT_CAFE_KAKAO = re.compile(r'사주카페|라이브카페|유아 > 놀이시설|보드카페|만화방')
    NOT_CAFE_LICENSE = {'한식', '뷔페식', '호프/통닭', '정종/대포집/소주방', '분식', '중국식', '일식', '식육(숯불구이)', '횟집', '탕류(보신용)', '냉면집',
                        '김밥(도시락)', '통닭(치킨)', '패밀리레스트랑', '외국음식전문점(인도,태국등)', '복어취급', '감성주점', '라이브카페', '출장조리', '편의점', '키즈카페'}
    CAFE_WORD = re.compile(r'카페|까페|커피|coffee|cafe|로스터|로스팅|바리스타|에스프레소|라떼|브루|베이커리|디저트|찻집|다방|다원|쌍화|전통차|빵|제과|케이크|도넛|와플|빙수|요거트|젤라또|티룸|tea')
    BAR_WORD = re.compile(r'호프|포차|맥주|술')
    # 이름만 봐도 카페가 아닌 말. 뒤의 것(골프, 교회 등)은 "골프장 안 카페"처럼 지점 이름일 수 있어서 카페라는 말이 없을 때만 뺀다.
    STRONG_NAME = re.compile(r'호프|포차|부동산|공인중개|당구|노래|pc방|피씨방|편의점|만화카페|키즈카페|보드게임|보드카페|스터디카페|독서실|웨딩|뷔페|학원|네일|식당')
    WEAK_NAME = re.compile(r'골프|스크린|교회|헤어|미용|모텔|펜션|세탁|약국|치킨')
    why = {}
    unmatched = 0
    for i in range(len(names)):
        if i in drop or bidx[i] >= 0:
            continue
        nm = names[i].lower()
        cafe_word = CAFE_WORD.search(nm) and not BAR_WORD.search(nm)
        k = kcat[i]
        if k is not None:
            if OK_KAKAO.search(k) and not NOT_CAFE_KAKAO.search(k):
                continue
            if i in addr_matched:
                # 이름은 다른데 건물 주소만 같아서 짝지은 카카오 장소가 카페가 아니었다. 엉뚱한 짝이므로 짝을 푼다.
                kcat[i] = None; kid[i] = 0; in_kakao[i] = 0; lats[i], lngs[i] = pub_lats[i], pub_lngs[i]
                unmatched += 1
                k = None
            elif NOT_CAFE_KAKAO.search(k):
                why[i] = '카카오 분류: ' + ' > '.join(k.split(' > ')[:4]); continue
            elif k in ('음식점', '음식점 > 양식') or cafe_word:
                continue
            else:
                why[i] = '카카오 분류: ' + ' > '.join(k.split(' > ')[:3]); continue
        if k is None:
            if STRONG_NAME.search(nm):
                why[i] = '이름'
            elif ltypes[i] in NOT_CAFE_LICENSE and not cafe_word:
                why[i] = '인허가 업태: ' + ltypes[i]
            elif WEAK_NAME.search(nm) and not cafe_word:
                why[i] = '이름'
    print('주소만 같아서 잘못 짝지었던 곳(짝을 풂)', unmatched)
    reasons = collections.Counter(w.split(':')[0] for w in why.values())
    print('카페가 아니라서 뺀 곳', len(why), dict(reasons))
    with open(os.path.join(workdir, 'dropped_notcafe.txt'), 'w', encoding='utf-8') as f:
        for i, w in why.items():
            f.write('%s' % '	'.join((w, names[i], roads[i])) + chr(10))
    drop.update(why)

    # 3-1. 인허가에만 있고 카페 목록(상가정보)에는 없는 카페를 더한다(사용자 2026-11-27: 블루보틀이 지도에 1곳뿐이다).
    #   블루보틀처럼 일반음식점(업태 기타, 경양식 등)으로 허가받은 카페가 많다. 2-1은 최근 열두 달, 업태 까페만 보므로 이런 곳이 빠졌다.
    #   후보: 영업 중인 인허가(휴게음식점, 일반음식점, 제과점) 가운데 이름으로 브랜드를 알아본 곳, 또는 이름에 카페, 커피 같은 말이 든 곳.
    #   확인: 카카오 전국 카페 목록에 같은 주소(또는 120m 안)에 이름이 비슷한 카페가 있어야 넣는다(김밥집 "푸드카페" 같은 곳이 빠진다).
    #         브랜드 매장은 카카오에서 못 찾아도 넣는다(브랜드면 카페가 확실하다). 다만 같은 브랜드가 200m 안에 이미 있으면 같은 가게로 본다.
    #   지도에 이미 있는 곳(200m 안 같은 브랜드, 80m 안 비슷한 이름, 이미 다른 줄과 짝지어진 카카오 장소)은 넣지 않는다.
    #   좌표: 공개용은 상가정보 건물 좌표(없으면 인허가 좌표를 바꾼 것), 내 컴퓨터용은 카카오 좌표. 이름은 인허가 이름(카카오 이름은 쓰지 않는다).
    import math
    import tm_wgs
    ADD_WORD = re.compile(r'카페|까페|커피|coffee|cafe|로스터|로스터리|에스프레소|브루잉', re.I)
    ADD_NOT = re.compile(r'호프|포차|부동산|공인중개|당구|노래|pc방|피씨방|편의점|만화|키즈|보드|스터디|독서실|웨딩|뷔페|학원|네일|식당|주점|술|룸카페|사주|타로|라이브|김밥|분식', re.I)
    KBAD = re.compile(r'사주카페|라이브카페|보드카페|만화방|만화카페|키즈카페|유아')
    GS = 0.002

    def cell(la, ln):
        return (int(la / GS), int(ln / GS))

    def near(grid, la, ln, m):
        c0 = cell(la, ln)
        rr = int(m / 111000 / GS) + 1
        for a in range(c0[0] - rr, c0[0] + rr + 1):
            for bb in range(c0[1] - rr, c0[1] + rr + 1):
                for it in grid.get((a, bb), ()):
                    if math.hypot((it[0] - la) * 111000, (it[1] - ln) * 88000) <= m:
                        yield it

    def dist(la, ln, la2, ln2):
        return math.hypot((la - la2) * 111000, (ln - ln2) * 88000)

    kgrid, kaddr = collections.defaultdict(list), collections.defaultdict(list)
    for pid, v in places.items():
        if not v[5].startswith('음식점 > 카페') or KBAD.search(v[5]):
            continue
        it = (v[4], v[3], pid, norm(v[0]))
        kgrid[cell(v[4], v[3])].append(it)
        ka = addr_key(v[1] or '')
        if ka:
            kaddr[ka].append(it)
    have = collections.defaultdict(list)          # 지금 남은 카페(카카오 좌표가 있으면 그것, 없으면 공공 좌표)
    for i in range(len(names)):
        if i in drop:
            continue
        have[cell(lats[i] / 1e5, lngs[i] / 1e5)].append((lats[i] / 1e5, lngs[i] / 1e5, i, norm(names[i])))
    cands = []
    for k, v in lic_all.items():
        for j, c in enumerate(v):
            if (k, j) in used:
                continue
            raw = c[5]
            b = brand_of(raw.replace(' ', ''))
            if not (b >= 0 or ADD_WORD.search(raw)) or (b < 0 and ADD_NOT.search(raw)):
                continue
            cands.append((k, j, c, b))
    need_b = set(x[0] for x in cands)
    bld2 = {}
    with open(os.path.join(workdir, 'buildings.csv'), encoding='utf-8', newline='') as f:
        r2 = csv.reader(f)
        next(r2)
        for row in r2:
            kk = addr_key(row[0])
            if kk in need_b and kk not in bld2:
                bld2[kk] = row
    add = collections.Counter()
    ROADPART = re.compile(r'(\S+(?:로|길))\s+((?:지하)?\d+(?:-\d+)?)')
    for k, j, c, b in cands:
        raw, n = c[5], c[0]
        row = bld2.get(k)
        if row:
            pla, pln = float(row[5]), float(row[4])
        elif c[8] is not None and c[9] is not None and c[8] > 0:
            pla, pln = tm_wgs.to_wgs(c[8], c[9])
            if not (33 < pla < 39 and 124 < pln < 132):
                add['좌표 이상'] += 1
                continue
        else:
            add['좌표 없음'] += 1
            continue
        # 이미 지도에 있는가(앞에서 더한 줄도 have에 들어 있다)
        same = False
        for la, ln, i, hn in near(have, pla, pln, 200 if b >= 0 else 80):
            if (b >= 0 and bidx[i] == b) or (dist(la, ln, pla, pln) <= 80 and similar(n, hn) >= 0.6):
                same = True
                break
        if same:
            add['이미 지도에 있음'] += 1
            continue
        # 카카오 카페 목록에서 찾기: 같은 주소 먼저, 없으면 120m 안
        hit = None
        for it in kaddr.get(k, ()):
            if similar(n, it[3]) >= 0.6 or (b >= 0 and brand_of(it[3]) == b):
                hit = it
                break
        if not hit:
            best = 0
            for it in near(kgrid, pla, pln, 120):
                sc = 1.0 if (b >= 0 and brand_of(it[3]) == b) else similar(n, it[3])
                if sc >= 0.7 and sc > best:
                    hit, best = it, sc
        if hit and hit[2] in taken:
            add['카카오 장소가 이미 지도에 있음'] += 1
            continue
        if not hit and b < 0:
            add['카카오에서 카페로 확인 안 됨'] += 1
            continue
        # 지역: 상가정보 건물이 있으면 그 행정동, 없으면 가장 가까운 카페의 행정동
        if row:
            sido, sgg, dong = row[1], row[2] or row[1], row[3] or '기타'
            si = sido_ix.setdefault(sido, len(sido_ix))
            gi = sgg_ix.setdefault((si, sgg), len(sgg_ix))
            di = dong_ix.setdefault((gi, dong), len(dong_ix))
        else:
            nb, bd = None, 1e9
            for la, ln, i, hn in near(have, pla, pln, 1500):
                d = dist(la, ln, pla, pln)
                if d < bd:
                    nb, bd = i, d
            if nb is None:
                add['지역을 몰라 못 넣음'] += 1
                continue
            di = dongs[nb]
        m = ROADPART.search(c[6])
        road = (m.group(1) + ' ' + m.group(2)) if m else c[6].split(',')[0]
        fm = FLOOR.search(c[6])
        ym = c[2]
        for cn, cb, cy in closed_all.get(k, ()):
            if cy and cy < ym and ((b >= 0 and cb == b) or (b < 0 and similar(n, cn) >= 0.6)):
                ym = cy
        disp = re.sub(r'^\s*(?:\(주\)|주식회사|㈜)\s*', '', raw).strip()
        names.append(disp); bidx.append(b); areas.append(0 if c[3] == '뷔페식' else round(c[4])); dongs.append(di); roads.append(road)
        floors.append(0 if not fm else -1 if fm.group(1) else int(fm.group(2)))
        since.append(ym); closed.append(False); ltypes.append(c[3]); kcat.append(None)
        pub_lats.append(round(pla * 1e5)); pub_lngs.append(round(pln * 1e5))
        if hit:
            taken.add(hit[2]); kid.append(int(hit[2])); in_kakao.append(1)
            lats.append(round(hit[0] * 1e5)); lngs.append(round(hit[1] * 1e5))
            add['브랜드, 카카오로 확인' if b >= 0 else '이름, 카카오로 확인'] += 1
        else:
            kid.append(0); in_kakao.append(0); lats.append(round(pla * 1e5)); lngs.append(round(pln * 1e5))
            add['브랜드, 카카오에 없지만 넣음'] += 1
        have[cell(pla, pln)].append((pla, pln, len(names) - 1, n))
    print('인허가에서 더한 카페(3-1)', dict(add))
    print('카카오 좌표', dict(kstat))
    print('카카오 좌표로 바꾼 카페', len(new_xy), '두 줄이라 한 줄로 합친 카페', len(dups))
if drop:
    keep = [i for i in range(len(names)) if i not in drop]
    names, lats, lngs, bidx, areas, dongs, roads, floors, in_kakao, kid, pub_lats, pub_lngs, since = (
        [arr[i] for i in keep] for arr in (names, lats, lngs, bidx, areas, dongs, roads, floors, in_kakao, kid, pub_lats, pub_lngs, since))
print(len(names), dict(stat))
ys = collections.Counter(y for y in since if y)
print('문 연 달을 아는 카페(남은 것)', sum(ys.values()), '최근 달:', sorted(ys.items())[-14:])
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
    'since': since,             # 문 연 달(YYYYMM, 인허가일자 기준). 모르면 0
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
