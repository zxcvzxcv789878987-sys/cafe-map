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
            lic_all[k].append([n, brand_of(n), ym_of(row[i_date]) if i_date is not None else 0, row[i_type] if i_type is not None else '',
                               area if 0 < area <= 30000 else 0.0, row[i_name].strip(), row[i_addr], is_general])
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
            used.add((k, bj))
    if k:
        at_addr[k].append(ym > 0)
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
    out, dups, kstat, addr_matched = kakao_match.match(names, lats, lngs, bidx, roads, places)
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
