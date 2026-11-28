# 카페가 든 건물의 건축물대장(건축HUB getBrTitleInfo)을 받아 승객용 승강기 수, 사용승인 연도, 건물 주차 대수를 모은다.
# 하루 한도가 있어 여러 날 나눠 받는다. 받은 것은 작업/info_src/bld_raw.json에 쌓이고, 다시 돌리면 이어서 받는다.
# 사용법: python -I -X utf8 building_info.py [--max 9000] [--workers 2]
#   매달 refresh.py가 부른다: 새 카페의 건물을 받고, 열두 달 지난 건물을 조금씩 다시 받는다.
#   끝나면 작업/info_src/bld.json({카페 이름표: [승강기, 사용승인 연도, 주차 대수]})을 만든다. cafe_info.py가 이것을 info/*.json에 붙인다.
# 지번은 상가정보의 건물관리번호(법정동코드 10자리, 대지 1 또는 산 2, 번 4자리, 지 4자리)에서 얻는다.
# 카페 목록의 도로명주소와 같은 건물(도로명, 건물번호)의 상가정보 줄을 찾아 쓴다. 못 찾은 카페는 빠진다.
import os, sys, re, csv, json, time, collections, urllib.request, urllib.parse, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
WORK = os.path.join(HERE, '작업')
SRC = os.path.join(WORK, 'info_src')
os.makedirs(SRC, exist_ok=True)
RAW = os.path.join(SRC, 'bld_raw.json')
MAX = int(sys.argv[sys.argv.index('--max') + 1]) if '--max' in sys.argv else 9000
KEY = open(os.path.join(HERE, 'datago_key.txt'), encoding='utf-8').read().strip()
URL = 'http://apis.data.go.kr/1613000/BldRgstHubService/getBrTitleInfo'
csv.field_size_limit(10 ** 9)

sys.path.insert(0, HERE)
src = open(os.path.join(HERE, 'cafe_info.py'), encoding='utf-8').read()
g = {}
exec(src[src.index('def imul'):src.index('s = open(os.path.join(ROOT')], g)     # index.html과 같은 이름표 계산
hash36 = g['hash36']

SIDO = {'서울': '서울', '부산': '부산', '대구': '대구', '인천': '인천', '대전': '대전', '울산': '울산', '세종': '세종', '경기': '경기', '강원': '강원',
        '충청북': '충북', '충북': '충북', '충청남': '충남', '충남': '충남', '전라북': '전북', '전북': '전북', '경상북': '경북', '경북': '경북',
        '경상남': '경남', '경남': '경남', '제주': '제주', '광주': '광전', '전라남': '광전', '전남': '광전'}
NUM = re.compile(r'^(?:지하)?(\d+(?:-\d+)?),?$')


def addr_key(addr):
    """build.py와 같은 '시도|시군구 도로명|건물번호' 키."""
    t = (addr or '').replace('(', ' (').split()
    if len(t) < 3:
        return None
    sd = next((v for k, v in SIDO.items() if t[0].startswith(k)), t[0][:2])
    for i in range(1, len(t) - 1):
        if t[i].endswith(('로', '길')):
            m = NUM.match(t[i + 1])
            if m:
                return sd + '|' + ' '.join(t[1:i + 1]) + '|' + m.group(1)
    return None


# 1. 도로명주소 키 -> 건물관리번호(앞 19자리 = 지번)와 동 이름
lot_of = {}
for fn in ('cafes_raw.csv', 'bread_raw.csv'):
    p = os.path.join(WORK, fn)
    if not os.path.exists(p):
        continue
    for r in csv.DictReader(open(p, encoding='utf-8')):
        m = r.get('건물관리번호') or ''
        k = addr_key(r.get('도로명주소'))
        if k and len(m) >= 19 and m[:19].isdigit() and k not in lot_of:
            lot_of[k] = (m[:19], (r.get('동정보') or '').strip())

s = open(os.path.join(ROOT, 'cafes.js'), encoding='utf-8').read()
D = json.loads(s[s.index('=') + 1:s.rindex(';')])
cafe_lot = {}
for i in range(len(D['name'])):
    d = D['dong'][D['dongOf'][i]]
    gg = D['sgg'][d[1]]
    sido, sg = D['sido'][gg[1]], gg[0]
    full = (sido if sg == sido else sido + ' ' + sg) + ' ' + D['road'][i]
    v = lot_of.get(addr_key(full))
    if v:
        cafe_lot[hash36(D['name'][i] + '|' + full)] = v
lots = sorted(set(v[0] for v in cafe_lot.values()))
print('지번을 찾은 카페', len(cafe_lot), '/', len(D['name']), '건물(지번)', len(lots), flush=True)

# 2. 받기(이어서)
raw = json.load(open(RAW, encoding='utf-8')) if os.path.exists(RAW) else {}
# 건물마다 받은 달(YYYYMM). 열두 달이 지난 건물은 다시 받아서 승강기, 주차 대수 변화를 따라간다. 날짜가 없는 옛 기록은 이번 달로 친다.
DATE = os.path.join(SRC, 'bld_date.json')
got_ym = json.load(open(DATE, encoding='utf-8')) if os.path.exists(DATE) else {}
NOW_YM = int(time.strftime('%Y%m'))
for l in raw:
    got_ym.setdefault(l, NOW_YM)


def save():
    json.dump(raw, open(RAW + '.tmp', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    os.replace(RAW + '.tmp', RAW)
    json.dump(got_ym, open(DATE + '.tmp', 'w', encoding='utf-8'), separators=(',', ':'))
    os.replace(DATE + '.tmp', DATE)


def ask(lot):
    p = {'sigunguCd': lot[:5], 'bjdongCd': lot[5:10], 'platGbCd': '1' if lot[10] == '2' else '0', 'bun': lot[11:15], 'ji': lot[15:19],
         'numOfRows': 100, 'pageNo': 1, '_type': 'json', 'serviceKey': KEY}
    time.sleep(0.4)     # 너무 자주 물으면 서버가 429로 막는다
    try:
        t = urllib.request.urlopen(urllib.request.Request(URL + '?' + urllib.parse.urlencode(p), headers={'User-Agent': 'Mozilla/5.0'}), timeout=60).read().decode('utf-8', 'replace')
    except urllib.error.HTTPError as e:
        if e.code == 429:
            raise OverflowError('너무 자주 물음(429)')
        raise
    if 'LIMITED_NUMBER_OF_SERVICE_REQUESTS' in t or 'EXCEEDS' in t.upper():
        raise OverflowError('하루 한도')
    d = json.loads(t)
    body = d['response']['body']
    items = body.get('items') or {}
    items = items.get('item', []) if isinstance(items, dict) else items
    items = items if isinstance(items, list) else [items]
    out = []
    for it in items:
        def n(k):
            try:
                return int(float(it.get(k) or 0))
            except ValueError:
                return 0
        out.append([it.get('dongNm') or '', n('totArea'), (it.get('useAprDay') or '')[:4], n('rideUseElvtCnt'),
                    n('indrAutoUtcnt') + n('oudrAutoUtcnt') + n('indrMechUtcnt') + n('oudrMechUtcnt')])
    return out


def months_ago(ym):
    return (NOW_YM // 100 * 12 + NOW_YM % 100) - (ym // 100 * 12 + ym % 100)


# 아직 안 받은 건물(새로 생긴 카페의 건물 포함)이 먼저, 그다음 열두 달이 지난 건물을 오래된 것부터.
todo = [l for l in lots if l not in raw]
old = sorted((l for l in lots if l in raw and months_ago(got_ym.get(l, NOW_YM)) >= 12), key=lambda l: got_ym.get(l, NOW_YM))
print('남은 건물', len(todo), '다시 받을 오래된 건물', len(old), '이번에 받을 최대', MAX, flush=True)
todo += old
# 한 건에 1~2초 걸리는 서버라서 동시에 몇 건씩 묻는다(--workers, 기본 4). 서버에 무리를 주지 않게 크게 늘리지 않는다.
import threading, concurrent.futures
WORKERS = int(sys.argv[sys.argv.index('--workers') + 1]) if '--workers' in sys.argv else 4
stop_ev = threading.Event()
cnt = collections.Counter()


def one(lot):
    if stop_ev.is_set():
        return lot, None
    for t in range(3):
        try:
            return lot, ask(lot)
        except OverflowError:
            if not stop_ev.is_set():
                print('하루 한도에 닿아 멈춘다. 내일 다시 돌리면 이어서 받는다.', flush=True)
            stop_ev.set()
            return lot, None
        except Exception:
            time.sleep(2 * (t + 1))
    return lot, None


last = time.time()
with concurrent.futures.ThreadPoolExecutor(WORKERS) as ex:
    for lot, items in ex.map(one, todo[:MAX]):
        if items is not None:
            raw[lot] = items
            got_ym[lot] = NOW_YM
            cnt['done'] += 1
        elif not stop_ev.is_set():
            cnt['fail'] += 1
            if cnt['fail'] >= 50 and cnt['fail'] > cnt['done']:
                print('서버가 계속 실패해서 멈춘다(나중에 다시 돌리면 이어서 받는다).', flush=True)
                stop_ev.set()
        if time.time() - last > 60:
            save()
            last = time.time()
            print('받는 중', cnt['done'], '실패', cnt['fail'], flush=True)
done, fail = cnt['done'], cnt['fail']
save()
print('이번에 받음', done, '실패', fail, '받아 둔 건물', len(raw), '/', len(lots), flush=True)

# 3. 카페별로 정리: 건물 동이 여럿이면 상가정보의 동 이름과 같은 동, 없으면 가장 넓은 동
out = {}
for cid, (lot, dong) in cafe_lot.items():
    items = raw.get(lot)
    if not items:
        continue
    pick = None
    if dong and len(items) > 1:
        dn = re.sub(r'\s', '', dong)
        pick = next((x for x in items if x[0] and re.sub(r'\s', '', x[0]) in (dn, dn + '동')), None)
    if pick is None:
        pick = max(items, key=lambda x: x[1])
    y = int(pick[2]) if pick[2].isdigit() and 1900 < int(pick[2]) <= 2100 else 0
    out[cid] = [pick[3], y, pick[4]]
json.dump(out, open(os.path.join(SRC, 'bld.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print('건축물대장이 붙는 카페', len(out), flush=True)
