# 카페 목록(cafes_raw.csv)에 브랜드와 매장 면적을 붙여 cafes.js를 만든다.
# 사용법: python -I -X utf8 build.py <작업폴더> <출력 cafes.js> <인허가 CSV...>
import csv, sys, re, json, collections, difflib, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from brands import BRANDS, KAKAO_BRAND, BAKERY, pat_in

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
        if any(pat_in(n, p) for p in pats):
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



BARE = re.compile(r'카페|까페|커피|coffee|cafe|점$')


def brand_shop_ok(a, k):
    """이름에 브랜드가 안 보이는 가게 a가 카카오의 브랜드 매장 k와 같은 가게인가(둘 다 norm 한 이름).
    두 이름의 같은 끝부분(지점 이름)을 떼고 남은 앞부분을 견준다.
    '카페블레스롤천안신불당점'과 '블레스롤천안신불당점'(카카오 쪽이 다 겹침)은 같은 가게,
    '명동커피'와 '블루보틀명동카페', '뚜레쥬르올림픽공원역점'과 '요거트아이스크림의정석올림픽공원역점'은 다른 가게다.
    (similar()는 커피, 카페 같은 말을 떼고 견주어 '명동'만 남아 같다고 보므로 여기서는 쓰지 않는다.)"""
    a1, b1 = a, k
    while a1 and b1 and a1[-1] == b1[-1]:
        a1, b1 = a1[:-1], b1[:-1]
    if not b1:
        return True
    # 남은 앞부분에서 카페, 커피 같은 말을 뗀다('봄봄영산점'과 '카페봄봄영산점'은 '카페'만 다르다).
    ca, cb = BARE.sub('', a1), BARE.sub('', b1)
    if not cb:
        return True
    if not ca:
        return False      # 카카오 이름 앞에 우리 이름에 없는 말(브랜드)이 더 붙어 있다('명동카페'와 '블루보틀명동카페')
    # 한쪽이 다른 쪽의 앞머리면 같은 상호다('메가'와 '메가MGC', '봄봄'과 '봄봄춘천근화'). 가운데에 든 것은 아니다('명동'과 '블루보틀명동').
    if ca.startswith(cb) or cb.startswith(ca):
        return True
    # 한 글자만 다른 같은 길이의 앞부분은 오타로 본다('디져트39'와 '디저트39', '까페051'과 '카페051').
    if len(a1) == len(b1) and sum(x != y for x, y in zip(a1, b1)) <= 1:
        return True
    return difflib.SequenceMatcher(None, a1, b1).ratio() >= 0.6


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
    # 건물 주소만으로 지은 짝 가운데 이름이 전혀 다른 것은 푼다(사용자 2026-11-28: 같은 건물의 '버거웍스'가 카페 '하슬라가배'의 카카오 장소를 차지했다).
    # '카페', '커피' 같은 말을 뗀 두 이름에 같은 두 글자가 하나도 없으면 전혀 다른 이름으로 본다. 푼 줄은 아래에서 이름으로 물은 답(kakao_kw)으로 다시 찾고,
    # 카카오에 같은 이름이 카페 아닌 곳(햄버거 등)으로 있으면 뒤의 '카페가 아닌 곳 빼기'에서 빠진다.
    def bigrams(s):
        return set(s[k:k + 2] for k in range(len(s) - 1))

    addr_unpaired = set()
    for i in sorted(addr_matched):
        if i in bread or i not in out:
            continue
        a0 = BARE.sub('', norm(names[i]))
        k0 = BARE.sub('', norm(places[out[i]][0]))
        if len(a0) >= 2 and len(k0) >= 2 and not (bigrams(a0) & bigrams(k0)):
            del out[i]
            addr_matched.discard(i)
            addr_unpaired.add(i)
    kstat['건물 주소로 짝 찾음'] -= len(addr_unpaired)
    kstat['건물 주소로 지은 짝인데 이름이 전혀 달라 풂'] = len(addr_unpaired)
    new_xy ={i: (places[pid][4], places[pid][3]) for i, pid in out.items()}
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
    if addr_unpaired:
        au = collections.Counter()
        for i in addr_unpaired:
            if i in why:
                au['카카오에서 카페 아닌 곳으로 확인돼 뺌'] += 1
            elif i in drop:
                au['다른 까닭으로 빠짐'] += 1
            elif kid[i]:
                au['이름으로 물어 제 짝을 찾음'] += 1
            elif '%s@%d,%d' % (names[i], pub_lats[i], pub_lngs[i]) not in kw:
                au['아직 이름으로 안 물어봄'] += 1
            else:
                au['카카오에 없어 공공 이름으로 둠'] += 1
        print('주소로만 짝지었다가 푼 곳', len(addr_unpaired), dict(au))
        with open(os.path.join(workdir, 'addr_unpaired.tsv'), 'w', encoding='utf-8') as f:
            f.write('우리 이름\t도로명\t한 일\n')
            for i in sorted(addr_unpaired):
                f.write('\t'.join((names[i], roads[i], why.get(i, '빠짐' if i in drop else '이름으로 찾음' if kid[i] else '카카오 짝 없이 둠'))) + '\n')

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
    # 카카오 장소를 차지한 줄 가운데 앞에서 뺀 줄(빵집, 카페 아닌 곳, 겹친 줄)이 있다. 그 장소는 지도에 없으니 다시 쓸 수 있게 한다.
    taken = set(str(kid[i]) for i in range(len(names)) if i not in drop and kid[i])
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
    why31 = {}     # 3-1에서 인허가 줄마다 넣지 않은 까닭(3-3 보고에 쓴다)
    for k, j, c, b in cands:
        raw, n = c[5], c[0]
        row = bld2.get(k)
        if row:
            pla, pln = float(row[5]), float(row[4])
        elif c[8] is not None and c[9] is not None and c[8] > 0:
            pla, pln = tm_wgs.to_wgs(c[8], c[9])
            if not (33 < pla < 39 and 124 < pln < 132):
                add['좌표 이상'] += 1; why31[(k, j)] = '좌표 이상'
                continue
        else:
            add['좌표 없음'] += 1; why31[(k, j)] = '좌표 없음'
            continue
        # 카카오 카페 목록에서 찾기: 같은 주소 먼저, 없으면 120m 안. 아직 아무 줄과도 짝지어지지 않은 장소를 먼저 고른다.
        # 브랜드 매장은 같은 브랜드 장소만, 브랜드 아닌 곳은 브랜드 아닌 장소하고만 이름을 견준다.
        # ('던킨 은평성모병원'이 '백미당 은평성모병원점'의 카카오 장소를 차지해 백미당이 빠지던 것을 막는다. 2026-11-27)
        def fit(it):
            kb = brand_of(it[3])
            if b >= 0:
                return 1.0 if kb == b else 0.0
            if kb >= 0:
                # 인허가 이름에는 브랜드가 안 보이지만 카카오는 브랜드 매장인 곳('카페블레스롤천안신불당점'과 '블레스롤 천안신불당점').
                # 같은 끝부분(지점 이름)을 떼고 남은 앞부분도 비슷해야 같은 가게로 본다('휴게소 커피코너'와 '할리스 OO휴게소점'은 아니다).
                if not brand_shop_ok(n, it[3]):
                    return 0.0
            return similar(n, it[3])
        hit = None
        same_addr = [it for it in kaddr.get(k, ()) if fit(it) >= 0.6]
        if same_addr:
            hit = min(same_addr, key=lambda it: (it[2] in taken, -fit(it)))
        else:
            best = None
            for it in near(kgrid, pla, pln, 120):
                sc = fit(it)
                if sc >= 0.7:
                    key = (it[2] in taken, -sc)
                    if best is None or key < best:
                        hit, best = it, key
        if hit and hit[2] in taken:
            add['카카오 장소가 이미 지도에 있음'] += 1; why31[(k, j)] = '카카오 장소가 이미 지도에 있음'
            continue
        # 이미 지도에 있는가(앞에서 더한 줄도 have에 들어 있다)
        #  이름이 비슷해도 브랜드가 다르거나 한쪽만 브랜드면 다른 가게다('테라로사 예술의전당지점'과 '공차 예술의전당점'처럼 지점 이름만 같은 곳).
        #  카카오에서 찾은 매장은 카카오에서 확인된 다른 줄과 겹치지 않는다(카카오 장소가 다르면 다른 가게다. 200m 안에 같은 브랜드가 둘 있는 곳이 빠지지 않게).
        same = False
        for la, ln, i, hn in near(have, pla, pln, 200 if b >= 0 else 80):
            if hit and kid[i]:
                continue
            if (b >= 0 and bidx[i] == b) or (b < 0 and bidx[i] < 0 and dist(la, ln, pla, pln) <= 80 and similar(n, hn) >= 0.6):
                same = True
                break
        if same:
            add['이미 지도에 있음'] += 1; why31[(k, j)] = '이미 지도에 있음'
            continue
        if not hit and (b < 0 or BRANDS[b][0] in BAKERY):   # 빵집, 도넛 브랜드는 카카오가 카페로 본 매장만
            add['카카오에서 카페로 확인 안 됨'] += 1; why31[(k, j)] = '카카오에서 카페로 확인 안 됨'
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
                add['지역을 몰라 못 넣음'] += 1; why31[(k, j)] = '지역을 몰라 못 넣음'
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
            add['브랜드, 카카오에 없지만 넣음'] += 1; why31[(k, j)] = '브랜드, 카카오에 없지만 넣음'
        have[cell(pla, pln)].append((pla, pln, len(names) - 1, n))
    print('인허가에서 더한 카페(3-1)', dict(add))

    # 3-2. 카카오가 체인으로 분류한 카페는 상호명이 달라도 그 브랜드로 본다(예: 공공데이터에는 "요거트아이스크림의정석 OO점"으로만 있는 요아정).
    bname = {re.sub(r'[^0-9a-z가-힣]', '', n.lower()): j for j, (n, _, _) in enumerate(BRANDS)}
    kb = collections.Counter()
    for i in range(len(names)):
        if i in drop or bidx[i] >= 0 or not kid[i]:
            continue
        v = places.get(str(kid[i]))
        if not v or not v[5].startswith('음식점 > 카페'):
            continue
        last = v[5].split(' > ')[-1]
        j = bname.get(re.sub(r'[^0-9a-z가-힣]', '', KAKAO_BRAND.get(last, last).lower()), -1)
        # 지점 이름만 같아서 짝지어진 다른 가게는 빼고 본다(사용자 2026-11-27: 뚜레쥬르올림픽공원역점이 같은 주소의 "요거트아이스크림의정석 올림픽공원역점"과
        # 짝이 되어 요아정이 됐다). 두 이름의 같은 끝부분(지점 이름)을 떼고 남은 앞부분이 비슷할 때만 그 브랜드로 본다.
        if j >= 0:
            if not brand_shop_ok(norm(names[i]), norm(v[0])):
                # 이름이 전혀 다른 가게가 지점 이름만 같아서 그 브랜드 매장의 카카오 장소를 차지하고 있었다
                # ('르빵 신세계강남점'이 '차지 신세계백화점 강남점'을 차지). 짝을 풀어서 3-3이 그 브랜드 매장을 넣게 한다.
                kid[i] = 0; in_kakao[i] = 0; kcat[i] = None
                lats[i], lngs[i] = pub_lats[i], pub_lngs[i]
                kb['(이름이 달라 짝을 풂)'] += 1
                continue
        if j >= 0:
            bidx[i] = j
            kb[BRANDS[j][0]] += 1
    print('카카오 분류로 브랜드를 정한 카페', sum(kb.values()), kb.most_common(12))

    # 3-3. 카카오에 있는 브랜드 매장인데 지도에 없는 곳을 채운다(사용자 2026-11-27: 차지가 네이버에 11곳인데 지도에 3곳).
    #   카카오 쪽 브랜드: 카카오 분류의 체인 이름(요거트아이스크림의정석은 요아정 등)을 먼저 보고, 분류가 '카페'처럼 일반이면 이름으로 본다.
    #   이름에 무인, 캡슐이 든 곳은 이름으로 브랜드를 정하지 않는다('스타벅스캡슐무인카페'는 스타벅스가 아니다).
    #   (1) 같은 브랜드의 지도 매장이 카카오 짝 없이 200m 안에 있으면 그 매장과 짝을 짓는다(이름이 달라 짝을 못 지었던 곳).
    #   (2) 없으면 새로 넣는다. 공개용 좌표와 행정동은 상가정보 건물(도로명주소로 찾음)에서 가져온다. 건물을 못 찾으면 넣지 않는다.
    #   (3) 같은 주소에 같은 브랜드의 폐업 신고만 있고 영업 중 신고가 없으면 카카오에 남은 옛 정보로 보고 넣지 않는다.
    #   매장마다 왜 빠졌었는지 작업/brand_audit.tsv에, 지도에는 있는데 카카오에 같은 브랜드가 없는 곳은 작업/brand_only_ours.tsv에 적는다.
    def kakao_brand(v):
        last = v[5].split(' > ')[-1]
        j = bname.get(re.sub(r'[^0-9a-z가-힣]', '', KAKAO_BRAND.get(last, last).lower()), -1)
        if j >= 0:
            return j
        if '무인' in v[0] or '캡슐' in v[0]:
            return -1
        return brand_of(norm(v[0]))

    kbrand = {}
    for pid, v in places.items():
        if v[5].startswith('음식점 > 카페') and not KBAD.search(v[5]):
            j = kakao_brand(v)
            if j >= 0:
                kbrand[pid] = j
    taken3 = set(str(kid[i]) for i in range(len(names)) if i not in drop and kid[i])
    loose = collections.defaultdict(list)     # 카카오 짝이 없는 브랜드 매장(공개 좌표)
    gone_b = collections.defaultdict(list)    # 앞에서 뺀 브랜드 줄
    for i in range(len(names)):
        if bidx[i] < 0:
            continue
        it = (pub_lats[i] / 1e5, pub_lngs[i] / 1e5, i, '')
        if i in drop:
            gone_b[cell(it[0], it[1])].append(it)
        elif not kid[i]:
            loose[cell(it[0], it[1])].append(it)
    want3 = [(pid, j) for pid, j in kbrand.items() if pid not in taken3]
    allb = collections.defaultdict(list)      # 지금 지도에 있는 브랜드 매장(공개 좌표). 같은 건물의 같은 이름이면 넣지 않는다.
    for i in range(len(names)):
        if i not in drop and bidx[i] >= 0:
            allb[cell(pub_lats[i] / 1e5, pub_lngs[i] / 1e5)].append((pub_lats[i] / 1e5, pub_lngs[i] / 1e5, i, norm(names[i])))
    need3 = set(addr_key(places[pid][1] or '') for pid, _ in want3) - {None}
    bld3 = {}
    with open(os.path.join(workdir, 'buildings.csv'), encoding='utf-8', newline='') as f:
        r3 = csv.reader(f)
        next(r3)
        for row in r3:
            kk = addr_key(row[0])
            if kk in need3 and kk not in bld3:
                bld3[kk] = row
    st3 = collections.Counter()
    audit = []
    for pid, j in sorted(want3, key=lambda x: x[0]):
        v = places[pid]
        kla, kln = v[4], v[3]
        k = addr_key(v[1] or '')
        # (1) 이름이 달라 짝을 못 지은 지도 매장
        best, bd = None, 201
        for la, ln, i, _ in near(loose, kla, kln, 200):
            if bidx[i] == j and not kid[i]:
                d = dist(la, ln, kla, kln)
                if d < bd:
                    best, bd = i, d
        # 큰 건물(백화점, 쇼핑몰)은 상가정보 건물 좌표와 카카오 매장 좌표가 수백 m 떨어진다. 같은 도로명 건물(공개 좌표 30m 안)에 있는 같은 브랜드도 같은 가게로 본다.
        brow = bld3.get(k)
        if best is None and brow:
            bla, bln = float(brow[5]), float(brow[4])
            for la, ln, i, _ in near(loose, bla, bln, 30):
                if bidx[i] == j and not kid[i]:
                    best = i
                    break
        if best is not None:
            i = best
            kid[i] = int(pid); in_kakao[i] = 1; lats[i], lngs[i] = round(kla * 1e5), round(kln * 1e5)
            why3 = '카카오와 짝을 못 지은 지도 매장(%s)이 있었음' % names[i]
            st3['지도 매장과 짝 지음'] += 1
            audit.append((BRANDS[j][0], v[0], v[1], why3, '짝 지음'))
            continue
        # 왜 빠졌었나: 같은 자리(150m 안)에서 뺀 같은 브랜드 줄, 같은 주소의 인허가
        why3 = None
        for la, ln, i, _ in near(gone_b, kla, kln, 150):
            if bidx[i] == j:
                if i in why:
                    why3 = '상가정보에 있었지만 카페 아님으로 뺌(%s)' % why[i]
                elif i in bread:
                    why3 = '상가정보에 빵/도넛으로 올라 있고 카카오 카페와 짝을 못 지음'
                elif closed[i]:
                    why3 = '상가정보에 있었지만 폐업 신고가 있고 카카오와 짝을 못 지어 뺌'
                else:
                    why3 = '상가정보에 같은 가게가 두 줄이라 합치다 빠짐'
                break
        lic_open = [c for c in lic_all.get(k, ()) if c[1] == j] if k else []
        lic_closed = [c for c in closed_all.get(k, ()) if c[1] == j] if k else []
        if lic_closed and not lic_open and why3 is None:
            st3['폐업 신고만 있어 안 넣음'] += 1
            audit.append((BRANDS[j][0], v[0], v[1], '같은 주소에 폐업 신고만 있음(카카오에 남은 옛 정보로 봄)', '안 넣음'))
            continue
        lic_j = [jj for jj, c in enumerate(lic_all.get(k, ())) if c[1] == j] if k else []
        if why3 is None:
            if lic_j:
                jj = lic_j[0]
                why3 = ('인허가 줄이 상가정보의 다른 줄과 먼저 짝지어져 후보에서 빠짐' if (k, jj) in used
                        else '인허가에서 더할 때 빠짐: ' + why31.get((k, jj), '후보가 아님(이름, 날짜 조건)'))
            else:
                why3 = '공공자료(상가정보, 인허가)에 없음'
        # 카카오 운영정책: 카카오에서 받은 이름과 목록은 저장, 공개하지 않는다(사용자 2026-11-28 결정: 인허가가 있는 곳만 넣는다).
        # 카카오에만 있는 매장은 넣지 않고 기록만 한다. 넣는 매장의 이름은 인허가 이름이다.
        if not lic_open:
            st3['카카오에만 있어 안 넣음'] += 1
            audit.append((BRANDS[j][0], v[0], v[1], why3, '카카오에만 있어 안 넣음(운영정책)'))
            continue
        row = bld3.get(k)
        if not row:
            st3['건물을 못 찾아 안 넣음'] += 1
            audit.append((BRANDS[j][0], v[0], v[1], why3, '건물 좌표를 못 찾아 안 넣음'))
            continue
        sido, sgg, dong = row[1], row[2] or row[1], row[3] or '기타'
        si = sido_ix.setdefault(sido, len(sido_ix))
        gi = sgg_ix.setdefault((si, sgg), len(sgg_ix))
        di = dong_ix.setdefault((gi, dong), len(dong_ix))
        road = row[0]
        pre = row[1] + ' ' + row[2] + ' '
        if road.startswith(pre):
            road = road[len(pre):]
        lc = lic_open[0]
        disp3 = re.sub(r'^\s*(?:\(주\)|주식회사|㈜)\s*', '', lc[5]).strip()
        # 카카오에 같은 가게가 두 번 올라 있는 곳(예: '매머드커피'와 바뀐 이름 '매머드익스프레스'). 같은 건물에 같은 브랜드, 비슷한 이름이 이미 있으면 넣지 않는다.
        bla, bln = float(row[5]), float(row[4])
        if any(bidx[i] == j and similar(norm(disp3), hn) >= 0.8 for _, _, i, hn in near(allb, bla, bln, 30)):
            st3['같은 건물에 같은 가게가 있어 안 넣음'] += 1
            audit.append((BRANDS[j][0], v[0], v[1], '카카오에 같은 가게가 두 번 올라 있음', '안 넣음'))
            continue
        fm3 = FLOOR.search(lc[6] or '')
        names.append(disp3); bidx.append(j); areas.append(0 if lc[3] == '뷔페식' else round(lc[4])); dongs.append(di); roads.append(road)
        floors.append(0 if not fm3 else -1 if fm3.group(1) else int(fm3.group(2)))
        since.append(lc[2]); closed.append(False); ltypes.append(lc[3]); kcat.append(v[5])
        pub_lats.append(round(float(row[5]) * 1e5)); pub_lngs.append(round(float(row[4]) * 1e5))
        lats.append(round(kla * 1e5)); lngs.append(round(kln * 1e5)); kid.append(int(pid)); in_kakao.append(1)
        taken3.add(pid)
        allb[cell(bla, bln)].append((bla, bln, len(names) - 1, norm(disp3)))
        st3['새로 넣음'] += 1
        audit.append((BRANDS[j][0], v[0], v[1], why3, '넣음'))
    print('카카오 브랜드 매장으로 채움(3-3)', dict(st3), collections.Counter(a[3].split('(')[0] for a in audit).most_common(8))
    # 겹친 줄 빼기: 카카오 짝이 없는 브랜드 매장인데, 40m 안의 같은 브랜드 카카오 매장을 이미 다른 줄이 차지했고
    # 그 근처에 같은 브랜드 카카오 매장이 그것 하나뿐이면 같은 가게가 두 줄로 들어온 것이다(상가정보 줄과 인허가 줄 등).
    kgrid3 = collections.defaultdict(list)
    for pid, j in kbrand.items():
        v = places[pid]
        kgrid3[cell(v[4], v[3])].append((v[4], v[3], pid, j))
    dup3 = 0
    for i in range(len(names)):
        if i in drop or bidx[i] < 0 or kid[i]:
            continue
        la, ln = pub_lats[i] / 1e5, pub_lngs[i] / 1e5
        same = [it for it in near(kgrid3, la, ln, 40) if it[3] == bidx[i]]
        if len(same) == 1 and same[0][2] in taken3:
            drop.add(i)
            dup3 += 1
    print('같은 가게가 두 줄이라 뺀 브랜드 매장', dup3)

    # 3-4. 브랜드 본사가 홈페이지에 올린 공식 매장 목록(작업/hq/<브랜드>.csv)으로 빠진 매장을 채운다(사용자 2026-11-28: 모든 브랜드 본사 목록으로 채우자).
    #   파일 첫 줄은 '매장명,도로명주소,출처,받은날'. 파일 이름은 brands.py의 표시 이름이다.
    #   (1) 본사 매장의 도로명주소로 상가정보 건물(작업/buildings.csv)을 찾는다. 공개 좌표와 행정동은 이 건물 것을 쓴다.
    #       주소로 못 찾으면 같은 시군구에 있는 같은 브랜드, 같은 지점 이름의 카카오 장소의 도로명주소로 건물을 찾는다(카카오는 주소 확인에만 쓴다).
    #   (2) 지도의 같은 브랜드 매장과 짝을 짓는다. 같은 건물(건물 좌표 30m 안)이 먼저, 그다음 200m 안의 비슷한 지점 이름. 한 매장은 한 번만 짝이 된다.
    #       그래도 남은 본사 매장은 150m 안에 짝 없는 같은 브랜드 매장이 있으면 이름만 다른 같은 가게로 본다(두 줄로 찍히지 않게).
    #   (3) 짝이 없는 본사 매장을 넣는다. 이름은 '브랜드 + 본사 매장명'(매장명에 브랜드가 있으면 그대로).
    #       카카오의 같은 브랜드 매장(같은 주소, 없으면 200m 안 비슷한 지점 이름)은 장소 번호와 내 컴퓨터용 좌표에만 쓴다. 카카오 이름은 쓰지 않는다.
    #       빵집, 도넛 브랜드는 카카오가 카페로 분류한 매장만 넣는다(대부분 빵만 파는 가게라서).
    #   (4) 지도에는 있는데 본사 목록에 없는 매장은 작업/hq_not_in_list.tsv에 적고, 카카오에도 없으면 숨긴다(아래). 본사 매장마다 한 일은 작업/hq_audit.tsv.
    hq_ok = set()       # 본사 목록에 있는 매장(짝지은 지도 매장과 새로 넣은 매장). 3-5에서 숨기지 않는다.
    hq_dir = os.path.join(workdir, 'hq')
    hq_files = sorted(fn for fn in os.listdir(hq_dir) if fn.endswith('.csv') and not fn.startswith('_')) if os.path.isdir(hq_dir) else []
    if hq_files:
        bix = {n: j for j, (n, _, _) in enumerate(BRANDS)}
        bix_n = {norm(n): j for j, (n, _, _) in enumerate(BRANDS)}
        SGG_TOK = re.compile(r'\S+(?:시|군|구)$')

        def brand_free(n, j):
            """norm 한 이름에서 브랜드 글자를 떼고 지점 이름만 남긴다."""
            for p in sorted((p.lstrip('^').partition('!')[0] for p in BRANDS[j][2]), key=len, reverse=True) + [norm(BRANDS[j][0])]:
                if p and p in n:
                    n = n.replace(p, '', 1)
                    break
            return n

        def road_parse(ad):
            """본사 주소에서 (시도 묶음 또는 None, '도로명|건물번호')를 뽑는다. 시도가 빠진 주소, '142번길'처럼 띄어 쓴 도로명,
            '백호2길23-13'처럼 붙여 쓴 건물번호, '지하 112'도 읽는다."""
            t = [x for x in re.split(r'[\s,]+', ad.replace('(', ' (')) if x]
            u = []
            for x in t:
                if u and ((re.match(r'^\d+번[가-힣]?길$', x) and u[-1].endswith(('로', '길')))
                          or (re.match(r'^\d+길$', x) and re.match(r'^[가-힣]{2,}$', u[-1]) and not u[-1].endswith(('시', '군', '구', '읍', '면', '동')))):
                    u[-1] += x
                    continue
                m = re.match(r'^(.+(?:로|길))(\d+(?:-\d+)?)$', x)
                if m:
                    u += [m.group(1), m.group(2)]
                    continue
                u.append(x)
            u = [x for x in u if x != '지하']
            for i in range(len(u) - 1):
                if i and u[i].startswith('('):
                    break
                if u[i].endswith(('로', '길')) and len(u[i]) >= 2:
                    m = NUM.match(u[i + 1])
                    if m:
                        sd = sido_code(u[0]) if i >= 1 and any(u[0].startswith(k) for k in SIDO) else None
                        return sd, u[i] + '|' + m.group(1)
            return None, None

        JIBUN = re.compile(r'(\S+?(?:동|리|가))\s*(\d+(?:-\d+)?)(?:번지)?(?=[\s,]|$)')

        def branch_sim(a, b):
            a, b = re.sub(r'점$', '', a), re.sub(r'점$', '', b)
            if not a or not b:
                return 0.0
            if a == b:
                return 1.0
            # 숫자가 다르면 다른 매장이다('용산아이파크몰1f'와 '용산아이파크몰6f', '1호점'과 '2호점').
            da, db = re.findall(r'\d+', a), re.findall(r'\d+', b)
            if da and db and da != db:
                return 0.5
            if len(a) >= 2 and len(b) >= 2 and (a in b or b in a):
                return 0.9
            return difflib.SequenceMatcher(None, a, b).ratio()

        hq_rows = []        # [브랜드 번호, 매장명, 도로명주소, 출처, 받은날, 주소 키]
        hq_bad = collections.Counter()
        for fn in hq_files:
            bn = fn[:-4]
            j = bix.get(bn, bix_n.get(norm(bn), -1))
            if j < 0:
                print('3-4: 브랜드 이름을 몰라 건너뜀', fn)
                continue
            seen4 = set()
            with open(os.path.join(hq_dir, fn), encoding='utf-8-sig', newline='') as f:
                for r4 in csv.DictReader(f):
                    nm4 = (r4.get('매장명') or '').strip()
                    ad4 = re.sub(r'\s+', ' ', (r4.get('도로명주소') or '').strip())
                    if not nm4 or not ad4:
                        hq_bad['매장명이나 주소가 빈 줄'] += 1
                        continue
                    key4 = (norm(nm4), addr_key(ad4) or ad4)
                    if key4 in seen4:
                        hq_bad['같은 매장이 두 줄(본사 목록)'] += 1
                        continue
                    seen4.add(key4)
                    hq_rows.append([j, nm4, ad4, (r4.get('출처') or '').strip(), (r4.get('받은날') or '').strip(), addr_key(ad4), road_parse(ad4)])
        hq_brands = sorted(set(h[0] for h in hq_rows))
        # 카카오의 브랜드 매장(브랜드별)
        kby = collections.defaultdict(list)
        for pid, j in kbrand.items():
            kby[j].append(pid)
        # 주소로 건물을 못 찾을 때를 위해 '도로명|건물번호'로도 건물을 모은다.
        def rn_of(k):
            p4 = k.split('|')
            return p4[1].split(' ')[-1] + '|' + p4[2]

        need4 = set(h[5] for h in hq_rows if h[5])
        road_num = set(h[6][1] for h in hq_rows if h[6][1])
        bld4, bld4_rn = {}, collections.defaultdict(list)

        def read_bld(keys, with_rn):
            with open(os.path.join(workdir, 'buildings.csv'), encoding='utf-8', newline='') as f:
                r4 = csv.reader(f)
                next(r4)
                for row in r4:
                    kk = addr_key(row[0])
                    if not kk:
                        continue
                    if kk in keys and kk not in bld4:
                        bld4[kk] = row
                    if with_rn and rn_of(kk) in road_num:
                        bld4_rn[rn_of(kk)].append(row)

        kalt = {}

        def find_bld(hi, h):
            if h[5] and h[5] in bld4:
                return bld4[h[5]], '주소'
            sd, rn = h[6]
            if rn:
                # 시도나 시군구 쓰는 법이 달라 키가 안 맞는 경우(인천 구 개편, 시도를 빼고 쓴 주소 등):
                # 같은 도로명, 건물번호의 건물을 모아 시도가 같고, 시군구 이름이 본사 주소에 든 곳이 하나뿐이면 그것.
                # 시군구 이름이 맞는 곳이 없으면 그 시도(시도를 안 쓴 주소는 전국)에 그 도로명, 건물번호가 한 곳뿐일 때만 그것.
                c0 = [row for row in bld4_rn.get(rn, ()) if sd is None or sido_code(row[1]) == sd]
                c4 = {(row[1], row[2]): row for row in c0 if row[2] and all(t in h[2] for t in row[2].split())}
                if len(c4) == 1:
                    return next(iter(c4.values())), '주소(시군구로 맞춤)'
                c4 = {(row[1], row[2]): row for row in c0}
                if len(c4) == 1:
                    return next(iter(c4.values())), '주소(도로명과 건물번호로 맞춤)'
            if hi in kalt and kalt[hi] in bld4:
                return bld4[kalt[hi]], '카카오 주소'
            # 상가정보 건물 목록에 없는 건물(가게가 인허가에만 올라 있는 곳): 같은 주소 인허가의 공공 좌표를 쓴다. 행정동은 가장 가까운 카페의 것.
            for k4 in (h[5], kalt.get(hi)):
                for c in lic_all.get(k4, ()) if k4 else ():
                    if c[8] is None or c[9] is None or c[8] <= 0:
                        continue
                    la4, ln4 = tm_wgs.to_wgs(c[8], c[9])
                    if not (33 < la4 < 39 and 124 < ln4 < 132):
                        continue
                    nb, bd = None, 1501
                    for la, ln, i, _ in near(have, la4, ln4, 1500):
                        d = dist(la, ln, la4, ln4)
                        if d < bd:
                            nb, bd = i, d
                    if nb is None:
                        continue
                    gi, dn = inv_dong[dongs[nb]]
                    si, sg = inv_sgg[gi]
                    sd4 = inv_sido[si]
                    road4 = re.sub(r'\s*[,(].*$', '', c[6]).strip()
                    return [road4, sd4, sg, dn, ln4, la4], '인허가 좌표'
            return None, ''

        inv_sido = {v: k for k, v in sido_ix.items()}
        inv_sgg = {v: k for k, v in sgg_ix.items()}
        inv_dong = {v: k for k, v in dong_ix.items()}
        read_bld(need4, True)
        # 주소로 건물을 못 찾은 매장은 카카오 도로명주소로 다시 찾는다
        for hi, h in enumerate(hq_rows):
            if find_bld(hi, h)[0] is not None:
                continue
            toks = [t for t in h[2].replace('(', ' (').split() if SGG_TOK.match(t)]
            # 지번 주소(봉곡동 236-10)는 카카오의 같은 브랜드 장소 가운데 지번이 같은 곳이 하나뿐이면 그 도로명주소를 쓴다.
            jm = JIBUN.search(h[2]) if not h[6][1] else None
            if jm:
                jw = jm.group(1) + ' ' + jm.group(2)
                c4 = [pid for pid in kby.get(h[0], ()) if (' ' + (places[pid][2] or '') + ' ').find(' ' + jw + ' ') >= 0
                      and (not toks or any(t in places[pid][2] for t in toks))]
                if len(c4) == 1:
                    ka4 = addr_key(places[c4[0]][1] or '')
                    if ka4:
                        kalt[hi] = ka4
                        continue
            bf = brand_free(norm(h[1]), h[0])
            best, bs, two = None, 0.0, False
            for pid in kby.get(h[0], ()):
                v = places[pid]
                if not toks or not any(t in (v[1] or '') + ' ' + (v[2] or '') for t in toks):
                    continue
                s = branch_sim(bf, brand_free(norm(v[0]), h[0]))
                if s >= 0.9:
                    if best is not None and s == bs:
                        two = True
                    if s > bs:
                        best, bs, two = pid, s, False
            if best and not two:
                ka4 = addr_key(places[best][1] or '')
                if ka4:
                    kalt[hi] = ka4
        if set(kalt.values()) - set(bld4):
            read_bld(set(kalt.values()) - set(bld4), False)


        allb4 = collections.defaultdict(list)      # 지금 지도에 있는 본사 목록 브랜드의 매장(공개 좌표)
        hqb = set(hq_brands)
        before4 = collections.Counter()
        for i in range(len(names)):
            if i not in drop and bidx[i] in hqb:
                allb4[cell(pub_lats[i] / 1e5, pub_lngs[i] / 1e5)].append((pub_lats[i] / 1e5, pub_lngs[i] / 1e5, i, brand_free(norm(names[i]), bidx[i])))
                before4[bidx[i]] += 1
        st4 = collections.Counter()
        audit4 = [None] * len(hq_rows)
        pos4 = {}
        pairs = []
        for hi, h in enumerate(hq_rows):
            row, how = find_bld(hi, h)
            if not row:
                st4['건물을 못 찾아 안 넣음'] += 1
                audit4[hi] = ('건물을 못 찾아 안 넣음', '')
                continue
            pos4[hi] = (row, how)
        # 본사 목록에 같은 매장이 두 줄로 올라 있는 곳(같은 건물, 비슷한 지점 이름: '부산시민회관점'과 '시민회관점')은 한 줄만 쓴다.
        grp4 = collections.defaultdict(list)
        for hi in sorted(pos4):
            h = hq_rows[hi]
            bf = brand_free(norm(h[1]), h[0])
            g = grp4[(h[0], pos4[hi][0][0])]
            # 이름이 같거나 한쪽이 다른 쪽을 품고(부산시민회관과 시민회관), 숫자도 같을 때만 같은 매장으로 본다('롯데동탄'과 '롯데시네마동탄'은 다르다).
            if any(branch_sim(bf, bf2) >= 0.9 for bf2 in g):
                st4['본사 목록에 같은 매장이 두 줄(같은 건물, 비슷한 이름)'] += 1
                audit4[hi] = ('본사 목록에 같은 매장이 두 줄(같은 건물, 비슷한 이름)', '')
                del pos4[hi]
                continue
            g.append(bf)
        # 짝 순서: 같은 건물의 비슷한 이름, 200m 안 비슷한 이름, 같은 건물의 다른 이름. 본사 목록에 주소가 잘못 적힌 줄이 같은 건물의 다른 매장을 먼저 차지하지 않게 한다.
        for hi, (row, how) in pos4.items():
            h = hq_rows[hi]
            bla, bln = float(row[5]), float(row[4])
            bf = brand_free(norm(h[1]), h[0])
            for la, ln, i, hn in near(allb4, bla, bln, 200):
                if bidx[i] != h[0]:
                    continue
                d = dist(la, ln, bla, bln)
                ns = branch_sim(bf, hn)
                if ns >= 0.7:
                    pairs.append((0 if d <= 30 else 1, -ns, d, hi, i))
                elif d <= 30:
                    pairs.append((2, -ns, d, hi, i))
        matched_h, matched_m = {}, {}
        for kind, _ns, d, hi, i in sorted(pairs):
            if hi in matched_h or i in matched_m:
                continue
            matched_h[hi], matched_m[i] = (i, 0 if kind == 2 else kind), hi
        for hi in pos4:
            if hi in matched_h:
                continue
            row = pos4[hi][0]
            bla, bln = float(row[5]), float(row[4])
            best, bd = None, 151
            for la, ln, i, hn in near(allb4, bla, bln, 150):
                if bidx[i] == hq_rows[hi][0] and i not in matched_m:
                    d = dist(la, ln, bla, bln)
                    if d < bd:
                        best, bd = i, d
            if best is not None:
                matched_h[hi], matched_m[best] = (best, 2), hi
        KIND = ('같은 건물에 있음', '200m 안 비슷한 이름으로 있음', '150m 안 같은 브랜드로 있음(이름만 다름)')
        for hi, (i, kind) in matched_h.items():
            st4[KIND[kind]] += 1
            audit4[hi] = (KIND[kind], names[i])
        taken4 = set(str(kid[i]) for i in range(len(names)) if i not in drop and kid[i])
        kaddr4 = collections.defaultdict(list)
        for j in hqb:
            for pid in kby.get(j, ()):
                ka4 = addr_key(places[pid][1] or '')
                if ka4:
                    kaddr4[ka4].append(pid)
        kgrid4 = collections.defaultdict(list)
        for j in hqb:
            for pid in kby.get(j, ()):
                v = places[pid]
                kgrid4[cell(v[4], v[3])].append((v[4], v[3], pid, j))
        n0 = len(names)
        # 본사 목록에 같은 지점이 주소만 달리 두 번 올라 있는 곳('공영로 75'와 '공영로 76', 지번과 도로명)을 알아보려고 지점 이름별로 모은다.
        by_name4 = collections.defaultdict(list)
        for hi in pos4:
            by_name4[(hq_rows[hi][0], re.sub(r'점$', '', brand_free(norm(hq_rows[hi][1]), hq_rows[hi][0])))].append(hi)
        done4 = set(matched_h)
        for hi, (row, how) in pos4.items():
            if hi in matched_h:
                continue
            j, nm4, ad4 = hq_rows[hi][0], hq_rows[hi][1], hq_rows[hi][2]
            bla, bln = float(row[5]), float(row[4])
            bf = brand_free(norm(nm4), j)
            twin = [hi2 for hi2 in by_name4[(j, re.sub(r'점$', '', bf))] if hi2 != hi and hi2 in done4
                    and dist(float(pos4[hi2][0][5]), float(pos4[hi2][0][4]), bla, bln) <= 500]
            if twin:
                st4['본사 목록에 같은 지점이 주소만 달리 두 줄(안 넣음)'] += 1
                audit4[hi] = ('본사 목록에 같은 지점이 주소만 달리 두 줄(500m 안)', '')
                continue
            kk = addr_key(row[0])
            # 카카오 짝: 같은 도로명주소의 같은 브랜드 장소, 없으면 200m 안 비슷한 지점 이름. 아직 지도의 다른 줄이 차지하지 않은 것만.
            hit = None
            c4 = [pid for pid in set(kaddr4.get(kk, []) + kaddr4.get(hq_rows[hi][5], [])) if kbrand[pid] == j and pid not in taken4]
            if c4:
                hit = max(c4, key=lambda pid: branch_sim(bf, brand_free(norm(places[pid][0]), j)))
            else:
                bs = 0.7
                for la, ln, pid, jj in near(kgrid4, bla, bln, 200):
                    if jj == j and pid not in taken4:
                        s = branch_sim(bf, brand_free(norm(places[pid][0]), j))
                        if s >= bs:
                            hit, bs = pid, s
            # 같은 건물에 같은 브랜드 매장이 이미 있는데 카카오에서 따로 확인되지 않으면 넣지 않는다(본사 목록의 주소 오류나 겹친 줄일 수 있다).
            same_b = [hn for _, _, i, hn in near(allb4, bla, bln, 30) if bidx[i] == j]
            if hit and same_b:
                # 카카오 장소가 이 본사 매장의 이름과 비슷하고, 같은 건물의 기존 매장 이름과는 달라야 따로 있는 매장으로 본다.
                kbf = brand_free(norm(places[hit][0]), j)
                if branch_sim(bf, kbf) < 0.7 or any(branch_sim(kbf, hn) >= 0.7 for hn in same_b):
                    hit = None
            if not hit and same_b:
                st4['같은 건물에 같은 브랜드가 있고 카카오로 확인 안 됨(안 넣음)'] += 1
                audit4[hi] = ('같은 건물에 같은 브랜드가 이미 있고 카카오로 확인 안 됨', '')
                continue
            if not hit and BRANDS[j][0] in BAKERY:
                st4['빵집 브랜드라 카카오 카페로 확인될 때만 넣음(안 넣음)'] += 1
                audit4[hi] = ('빵집 브랜드인데 카카오 카페로 확인 안 됨', '')
                continue
            sido, sgg, dong = row[1], row[2] or row[1], row[3] or '기타'
            si = sido_ix.setdefault(sido, len(sido_ix))
            gi = sgg_ix.setdefault((si, sgg), len(sgg_ix))
            di = dong_ix.setdefault((gi, dong), len(dong_ix))
            road = row[0]
            pre = row[1] + ' ' + row[2] + ' '
            if road.startswith(pre):
                road = road[len(pre):]
            disp4 = nm4 if (brand_of(norm(nm4)) == j or norm(BRANDS[j][0]) in norm(nm4)) else BRANDS[j][0] + ' ' + nm4
            # 넓이와 문 연 달: 같은 주소의 같은 브랜드 영업 중 인허가가 있으면 그것.
            lc = next((c for c in lic_all.get(kk, ()) if c[1] == j), None) if kk else None
            fm4 = FLOOR.search(ad4)
            names.append(disp4); bidx.append(j); dongs.append(di); roads.append(road)
            areas.append(0 if not lc or lc[3] == '뷔페식' else round(lc[4]))
            floors.append(0 if not fm4 else -1 if fm4.group(1) else int(fm4.group(2)))
            since.append(lc[2] if lc else 0); closed.append(False); ltypes.append(lc[3] if lc else '')
            pub_lats.append(round(bla * 1e5)); pub_lngs.append(round(bln * 1e5))
            if hit:
                v = places[hit]
                kcat.append(v[5]); kid.append(int(hit)); in_kakao.append(1); taken4.add(hit)
                lats.append(round(v[4] * 1e5)); lngs.append(round(v[3] * 1e5))
                st4['새로 넣음(카카오로 확인)'] += 1
                audit4[hi] = ('넣음(카카오로 확인, 건물은 %s로 찾음)' % how, disp4)
            else:
                kcat.append(None); kid.append(0); in_kakao.append(0)
                lats.append(round(bla * 1e5)); lngs.append(round(bln * 1e5))
                st4['새로 넣음(카카오에 없음)'] += 1
                audit4[hi] = ('넣음(카카오에 없음, 건물은 %s로 찾음)' % how, disp4)
            allb4[cell(bla, bln)].append((bla, bln, len(names) - 1, bf))
            done4.add(hi)
        hq_ok = set(matched_m) | set(range(n0, len(names)))
        print('본사 공식 목록으로 채움(3-4)', len(hq_files), '개 브랜드', len(hq_rows), '매장', dict(st4), dict(hq_bad))
        with open(os.path.join(workdir, 'hq_audit.tsv'), 'w', encoding='utf-8') as f:
            f.write('브랜드\t본사 매장명\t본사 주소\t한 일\t지도 이름\t출처\n')
            for hi, h in enumerate(hq_rows):
                a = audit4[hi]
                f.write('\t'.join((BRANDS[h[0]][0], h[1], h[2], a[0], a[1], h[3])) + '\n')
        # 지도에는 있는데 본사 목록에 없는 매장(사용자 2026-11-28 기준):
        #   카카오에도 같은 브랜드 매장으로 없으면 숨긴다(문 닫았을 가능성이 크다). 카카오에 있으면 지도에 둔다.
        #   본사 목록의 지점 이름과 같으면(본사 주소를 못 읽었거나 주소가 달라 짝을 못 지은 곳) 숨기지 않는다.
        #   받은 본사 목록이 지도 매장 수의 절반이 안 되는 브랜드는 목록이 덜 받힌 것일 수 있어 숨기지 않는다.
        hq_cnt = collections.Counter(h[0] for h in hq_rows)
        hq_names = collections.defaultdict(set)
        for h in hq_rows:
            hq_names[h[0]].add(re.sub(r'점$', '', brand_free(norm(h[1]), h[0])))
        thin = set(j for j in hqb if hq_cnt[j] < before4[j] * 0.5)
        if thin:
            print('3-4: 본사 목록이 지도 매장 수의 절반이 안 돼 숨기지 않는 브랜드', [BRANDS[j][0] for j in thin])
        nin, hid4 = collections.Counter(), collections.Counter()
        with open(os.path.join(workdir, 'hq_not_in_list.tsv'), 'w', encoding='utf-8') as f:
            f.write('브랜드\t지도 이름\t도로명\t카카오 장소 번호\t한 일\n')
            for i in range(len(names)):
                if i >= n0 or i in drop or bidx[i] not in hqb or i in matched_m:
                    continue
                j = bidx[i]
                nin[j] += 1
                if kid[i] and kbrand.get(str(kid[i])) == j:
                    memo = '본사 목록에 없음, 카카오에는 있어 지도에 둠'
                elif re.sub(r'점$', '', brand_free(norm(names[i]), j)) in hq_names[j]:
                    memo = '본사 목록에 같은 지점 이름이 있어 지도에 둠(주소로 짝을 못 지음)'
                elif j in thin:
                    memo = '본사 목록이 덜 받혔을 수 있어 지도에 둠'
                elif not any(re.sub(r'^(?:카페|까페|cafe)', '', norm(names[i])).startswith(p) or norm(names[i]).startswith(p)
                             for p in [q.lstrip('^').partition('!')[0] for q in BRANDS[j][2]] + [norm(BRANDS[j][0])] if p):
                    # '고모리커피공장'의 '모리커피'처럼 이름 가운데에 브랜드 글자가 우연히 든 다른 가게일 수 있다.
                    memo = '이름이 브랜드로 시작하지 않아 다른 가게일 수 있어 지도에 둠'
                else:
                    memo = '본사 목록에도 카카오에도 없어 숨김(문 닫았을 수 있음)'
                    drop.add(i)
                    hid4[j] += 1
                f.write('\t'.join((BRANDS[j][0], names[i], roads[i], str(kid[i] or ''), memo)) + '\n')
        print('본사 목록에도 카카오에도 없어 숨긴 매장', sum(hid4.values()))
        after4 = collections.Counter(bidx[i] for i in range(len(names)) if i not in drop and bidx[i] in hqb)
        with open(os.path.join(workdir, 'hq_report.tsv'), 'w', encoding='utf-8') as f:
            f.write('브랜드\t전\t본사 목록\t지금\t본사 목록에 없는 지도 매장\t그중 숨김\n')
            for j in sorted(hqb, key=lambda j: -hq_cnt[j]):
                f.write('%s\t%d\t%d\t%d\t%d\t%d\n' % (BRANDS[j][0], before4[j], hq_cnt[j], after4[j], nin[j], hid4[j]))
        print('지도에 있는데 본사 목록에 없는 매장', sum(nin.values()))

    # 3-5. 카카오에도 인허가에도 없는 카페(카카오 장소 번호도, 문 연 달도 없는 곳)를 정리한다(사용자 2026-11-28: "무조건 가장 정확해야지").
    #   상가정보에만 남은 문 닫은 가게가 많다(수원 파장로 113 아키리아커피스페이스: 코너드커피로 바뀐 뒤 문 닫음). 본사 목록에 있는 매장은 건드리지 않는다.
    #   (1) 그 자리(같은 도로명주소, 또는 공공 좌표 30m 안)의 카카오 카페와, 이름으로 물은 답(kakao_kw) 가운데 150m 안의 먹고 마시는 곳을 본다.
    #   (2) 이름이 비슷한 카카오 장소가 있으면 같은 가게로 보고 둔다(오타, 회사 이름이 붙은 이름 등). 장소 번호를 붙인다.
    #       그 장소를 지도의 다른 줄이 이미 차지했으면 같은 가게가 두 줄인 것이라 이 줄을 숨긴다.
    #   (3) 그 자리에 이름이 다른 카페만 있으면 가게가 바뀐 것으로 본다. 같은 주소의 영업 중 인허가에 그 카페가 있으면
    #       이 줄을 인허가 이름, 넓이, 문 연 달로 바꾼다(카카오 이름은 쓰지 않는다). 인허가에도 없으면 옛 가게로 보고 숨긴다.
    #       인허가의 그 카페가 이미 지도의 다른 줄로 있으면 이 줄은 숨긴다.
    #   (4) 그 자리에 카카오 카페가 하나도 없고 이름으로 물어도 안 나오면 숨긴다.
    #   카카오에서 본 이름, 주소는 어디에도 남기지 않는다. 한 일은 작업/nokakao_audit.tsv(우리 이름, 인허가 이름, 장소 번호만).
    inv_sido5 = {v: k for k, v in sido_ix.items()}
    inv_sgg5 = {v: k for k, v in sgg_ix.items()}
    inv_dong5 = {v: k for k, v in dong_ix.items()}

    def row_key(i):
        gi, _dn = inv_dong5[dongs[i]]
        si, sg = inv_sgg5[gi]
        sd = inv_sido5[si]
        r0 = roads[i]
        return addr_key(r0 if r0.startswith(sd) else sd + ' ' + ('' if sg == sd else sg + ' ') + r0)

    def bigram_dice(a, b):
        ga, gb = set(a[k:k + 2] for k in range(len(a) - 1)), set(b[k:k + 2] for k in range(len(b) - 1))
        return 2 * len(ga & gb) / (len(ga) + len(gb)) if ga and gb else 0.0

    def head_of(raw):
        """지점 이름(마지막 '...점')을 떼고 카페, 커피 같은 말을 뺀 상호."""
        t = raw.split()
        if len(t) >= 2 and t[-1].endswith('점'):
            t = t[:-1]
        return BARE.sub('', norm(' '.join(t)))

    def same_shop(raw, b, pid, kname):
        """우리 이름 raw(브랜드 b)와 카카오 장소 pid(이름 kname)가 같은 가게인가."""
        jb = kbrand.get(pid, -1)
        if b >= 0 and jb >= 0:
            return jb == b
        a, k = norm(raw), norm(kname)
        if not a or not k:
            return False
        if a == k:
            return True
        if not head_of(raw) or not head_of(kname):
            return False      # '카페', '더카페점'처럼 상호가 없는 이름은 똑같을 때만(아무 'OO카페'와 짝지어지지 않게)
        if brand_shop_ok(a, k) or brand_shop_ok(k, a):
            return True
        if jb >= 0:
            return False      # 카카오 쪽만 브랜드 매장이면 우리 이름에 그 브랜드가 보여야 한다('명동커피'와 '블루보틀 명동')
        ha, hk = head_of(raw), head_of(kname)
        s, l = (ha, hk) if len(ha) <= len(hk) else (hk, ha)
        if len(s) >= 2 and s in l:
            return True       # '서원컴퍼니풀덤 전대점'과 '풀덤 전남대점'
        return bigram_dice(ha, hk) >= 0.5

    taken5 = {}
    live_at = collections.defaultdict(list)
    live_xy = collections.defaultdict(list)       # 지금 남은 카페의 공공 좌표
    for i in range(len(names)):
        if i in drop:
            continue
        live_xy[cell(pub_lats[i] / 1e5, pub_lngs[i] / 1e5)].append((pub_lats[i] / 1e5, pub_lngs[i] / 1e5, i))
        if kid[i]:
            taken5[str(kid[i])] = i
        k5 = row_key(i)
        if k5:
            live_at[k5].append(i)
    st5, brand5 = collections.Counter(), collections.Counter()
    audit5 = []
    for i in range(len(names)):
        if i in drop or kid[i] or since[i] or i in hq_ok or i in bread:
            continue
        la, ln = pub_lats[i] / 1e5, pub_lngs[i] / 1e5
        k5 = row_key(i)
        docs = kw.get('%s@%d,%d' % (names[i], pub_lats[i], pub_lngs[i]))
        if docs is None:
            st5['아직 이름으로 안 물어봐서 둠'] += 1
            continue
        info = {}
        for it in list(kaddr.get(k5, ()) if k5 else ()) + list(near(kgrid, la, ln, 30)):
            v = places[it[2]]
            info[it[2]] = (v[4], v[3], v[5], v[0])
        spot = list(info)          # 그 자리의 카카오 카페
        for pid, pn, _r, x, y, cat in docs:
            if pid not in info and cat.startswith('음식점') and not KBAD.search(cat) and dist(y, x, la, ln) <= 150:
                info[pid] = (y, x, cat, pn)
        same = [pid for pid in info if same_shop(names[i], bidx[i], pid, info[pid][3])]
        old, new_name, pid_set = names[i], '', ''
        if same:
            free = [pid for pid in same if pid not in taken5]
            if free:
                pid = min(free, key=lambda p: dist(info[p][0], info[p][1], la, ln))
                kid[i], kcat[i], in_kakao[i] = int(pid), info[pid][2], 1
                lats[i], lngs[i] = round(info[pid][0] * 1e5), round(info[pid][1] * 1e5)
                taken5[pid] = i
                pid_set = pid
                act = '같은 가게로 보고 둠(카카오 장소 번호 붙임)'
            else:
                drop.add(i)
                act = '같은 가게가 지도에 이미 있어 숨김'
        elif spot:
            lc, lpid = None, None
            for c in lic_all.get(k5, ()) if k5 else ():
                hit5 = [pid for pid in spot if same_shop(c[5], c[1], pid, info[pid][3])]
                if hit5:
                    lc, lpid = c, hit5[0]
                    break
            if lc is None:
                drop.add(i)
                act = '그 자리에 이름이 다른 카페만 있고 인허가에 없어 숨김(옛 가게)'
            elif any(j != i and j not in drop and (similar(norm(names[j]), lc[0]) >= 0.6 or (lc[1] >= 0 and bidx[j] == lc[1]))
                     for j in set(live_at.get(k5, ())) | set(it[2] for it in near(live_xy, la, ln, 50))):
                # 같은 주소 또는 50m 안(주소에 읍면을 쓰고 안 쓰는 차이로 키가 다른 줄: '광혜원면 장기길 45'와 '장기길 45')
                drop.add(i)
                act = '바뀐 가게가 이미 지도에 있어 숨김'
            else:
                ym = lc[2]
                for cn, cb, cy in closed_all.get(k5, ()):
                    if cy and cy < ym and ((lc[1] >= 0 and cb == lc[1]) or (lc[1] < 0 and similar(lc[0], cn) >= 0.6)):
                        ym = cy     # 같은 자리, 같은 이름으로 허가를 새로 받은 가게는 처음 허가 달을 쓴다(2번과 같은 규칙)
                names[i] = new_name = lc[5]
                bidx[i] = brand_of(lc[5].replace(' ', ''))
                since[i], ltypes[i] = ym, lc[3]
                areas[i] = 0 if lc[3] == '뷔페식' else round(lc[4])
                if lpid not in taken5:
                    kid[i], kcat[i], in_kakao[i] = int(lpid), info[lpid][2], 1
                    lats[i], lngs[i] = round(info[lpid][0] * 1e5), round(info[lpid][1] * 1e5)
                    taken5[lpid] = i
                    pid_set = lpid
                act = '가게가 바뀌어 인허가 이름으로 바꿈'
        else:
            drop.add(i)
            act = '그 자리에 카카오 카페가 없어 숨김'
        st5[act] += 1
        if bidx[i] >= 0 or brand_of(old.replace(' ', '')) >= 0:
            brand5[act] += 1
        audit5.append((act, old, roads[i], new_name, pid_set))
    print('카카오에도 인허가에도 없던 카페(3-5)', sum(st5.values()), dict(st5), '그중 브랜드', dict(brand5))
    with open(os.path.join(workdir, 'nokakao_audit.tsv'), 'w', encoding='utf-8') as f:
        f.write('한 일\t우리 이름\t도로명\t바꾼 이름(인허가)\t카카오 장소 번호\n')
        for a in audit5:
            f.write('\t'.join(a) + '\n')

    with open(os.path.join(workdir, 'brand_audit.tsv'), 'w', encoding='utf-8') as f:
        f.write('브랜드\t카카오 이름\t카카오 주소\t빠졌던 이유\t한 일\n')
        for a in audit:
            f.write('\t'.join(a) + '\n')
    # 지도에는 있는데 카카오에 같은 브랜드 매장으로 없는 곳
    with open(os.path.join(workdir, 'brand_only_ours.tsv'), 'w', encoding='utf-8') as f:
        f.write('브랜드\t우리 이름\t도로명\t카카오에서 짝지은 장소\t이유\n')
        oc = collections.Counter()
        for i in range(len(names)):
            if i in drop or bidx[i] < 0:
                continue
            p = str(kid[i]) if kid[i] else None
            if p and kbrand.get(p) == bidx[i]:
                continue
            if p:
                w = '카카오에는 다른 이름으로 올라 있음'
                kn = places[p][0] if p in places else ''
            else:
                w = '카카오에서 못 찾음(문을 닫았거나 카카오에 없는 곳)'
                kn = ''
            oc[w] += 1
            f.write('\t'.join((BRANDS[bidx[i]][0], names[i], roads[i], kn, w)) + '\n')
    print('지도에만 있는 브랜드 매장', dict(oc))
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
