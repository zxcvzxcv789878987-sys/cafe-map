# 지도 자료를 처음부터 끝까지 새로 받아서 다시 만들고, 이상이 없으면 인터넷 주소에 올린다. 한 달에 한 번 돌린다.
# 사용법: python -X utf8 "데이터 만들기/refresh.py"            (전부)
#         python -X utf8 "데이터 만들기/refresh.py" --no-push  (올리지는 않고 만들기만)
#
# 순서
#   1. 카페 목록: 소상공인시장진흥공단 상가(상권)정보 (공공데이터포털 15083033, 3개월마다 새 파일이 나온다)
#   2. 넓이, 영업 상태, 문 연 달: 행정안전부 인허가 자료 3종 (휴게음식점, 제과점, 일반음식점)
#      카페 목록에 아직 없는 최근 열두 달의 개업 카페도 여기서 더한다(build.py 2-1).
#   3. 카카오맵의 전국 카페 목록(좌표, 장소 번호)과 이름으로 다시 물어보기
#   3-1. 브랜드 본사 매장 목록(hq_fetch 폴더의 브랜드별 받기 스크립트)
#   4. cafes.js(올리는 것, 공공데이터 좌표)와 cafes.local.js(이 컴퓨터용, 카카오 좌표) 만들기
#      카카오에도 인허가에도 없는 카페는 그 자리의 카카오 카페로 확인해 숨기거나 인허가 이름으로 바꾼다(build.py 3-5).
#   5. 점검: 카페 수가 지난번과 크게 다르면 멈추고 예전 파일을 그대로 둔다
#   6. 깃허브에 올리기
#   지하철 노선, 역, 아파트(landmarks.js)는 석 달에 한 번 fetch_landmarks.py로 다시 받는다
#   0, 7. 키 점검(check_keys.py), 새 법정구역 파일 점검(check_legal.py), 새 브랜드 후보(brand_candidates.py)를 기록에 남긴다
# 받은 원본은 "데이터 만들기/작업" 폴더에 둔다(깃허브에는 올리지 않는다).
import sys, os, json, re, time, shutil, subprocess, urllib.request, urllib.parse, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
WORK = os.path.join(HERE, '작업')
os.makedirs(WORK, exist_ok=True)
NO_PUSH = '--no-push' in sys.argv
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36'
LOG = open(os.path.join(WORK, 'refresh.log'), 'a', encoding='utf-8')
STATE_PATH = os.path.join(WORK, 'state.json')
state = json.load(open(STATE_PATH, encoding='utf-8')) if os.path.exists(STATE_PATH) else {}


def say(*a):
    line = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S ') + ' '.join(str(x) for x in a)
    print(line, flush=True)
    LOG.write(line + '\n'); LOG.flush()


def stop(msg):
    say('멈춤:', msg)
    sys.exit(1)


def download(url, path, headers=None, data=None):
    """큰 파일을 조금씩 받아 저장한다. 다 받은 뒤에 이름을 바꿔서, 받다 만 파일이 남지 않게 한다."""
    req = urllib.request.Request(url, data=data, headers=dict({'User-Agent': UA}, **(headers or {})))
    tmp = path + '.part'
    with urllib.request.urlopen(req, timeout=120) as r, open(tmp, 'wb') as f:
        n = 0
        while True:
            b = r.read(1 << 20)
            if not b:
                break
            f.write(b); n += len(b)
    os.replace(tmp, path)
    return n


def run(script, *args):
    """같은 폴더의 다른 스크립트를 돌리고 마지막 줄들을 돌려준다. 실패하면 멈춘다."""
    p = subprocess.run([sys.executable, '-I', '-X', 'utf8', os.path.join(HERE, script)] + list(args), cwd=ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace')
    tail = (p.stdout or '').strip().splitlines()[-12:]
    for line in tail:
        say('   ', line)
    if p.returncode != 0:
        stop(script + ' 실패: ' + (p.stderr or '')[-600:])
    return '\n'.join(tail)


def count(path):
    d = json.loads(open(path, encoding='utf-8').read()[len('window.CAFES='):-1])
    return len(d['name']), sum(1 for x in d.get('kid', []) if x)


say('==== 갱신 시작 ====')
# 0. 키 점검: 공공데이터, 카카오 키가 살아 있는지 한 번씩 물어본다. 문제가 있어도 멈추지 않고 보고에 남긴다.
key_report = run('check_keys.py')
legal_report = run('check_legal.py')     # 새 법정구역 파일이 나왔는지(받기는 사람이)

# 1. 카페 목록
say('1. 상가정보 파일 확인')
page = urllib.request.urlopen(urllib.request.Request('https://www.data.go.kr/data/15083033/fileData.do', headers={'User-Agent': UA}), timeout=60).read().decode('utf-8', 'replace')
m = re.search(r"fn_fileDataDown\('15083033',\s*'(uddi:[0-9a-f-]+)'", page)
if not m:
    stop('공공데이터포털 화면에서 파일 번호를 찾지 못했다(화면이 바뀐 것 같다).')
body = urllib.parse.urlencode({'publicDataPk': '15083033', 'publicDataDetailPk': m.group(1), 'fileDetailSn': '1'}).encode()
info = json.load(urllib.request.urlopen(urllib.request.Request('https://www.data.go.kr/tcs/dss/selectFileDataDownload.do', data=body, headers={'User-Agent': UA, 'Referer': 'https://www.data.go.kr/data/15083033/fileData.do'}), timeout=60))
atch = re.search(r'"atchFileId"\s*:\s*"([^"]+)"', json.dumps(info))
if not atch:
    stop('상가정보 파일 번호(atchFileId)를 받지 못했다.')
zip_path = os.path.join(WORK, 'sangga.zip')
if state.get('sangga') == atch.group(1) and os.path.exists(zip_path) and os.path.exists(os.path.join(WORK, 'cafes_raw.csv')) and os.path.exists(os.path.join(WORK, 'buildings.csv')):
    say('   지난번과 같은 파일이라 다시 받지 않는다.')
else:
    n = download('https://www.data.go.kr/cmm/cmm/fileDownload.do?atchFileId=%s&fileDetailSn=1' % atch.group(1), zip_path)
    say('   받음', n // (1 << 20), 'MB')
    run('extract.py', zip_path, WORK)
    state['sangga'] = atch.group(1)

# 2. 인허가 자료
say('2. 인허가 자료 받기')
lic = []
for name in ('rest_cafes', 'bakeries', 'general_restaurants'):
    path = os.path.join(WORK, name + '.csv')
    n = download('https://file.localdata.go.kr/file/download/%s/info' % name, path, headers={'Referer': 'https://www.localdata.go.kr/'})
    say('   ', name, n // (1 << 20), 'MB')
    if n < 5 << 20:
        stop(name + ' 파일이 너무 작다. 받는 주소가 바뀐 것 같다.')
    lic.append(path)

# 3. 카카오맵 전국 카페 목록 (키가 있을 때만)
places = os.path.join(HERE, 'kakao_places.json')
if os.path.exists(os.path.join(HERE, 'kakao_key.txt')):
    say('3. 카카오맵 전국 카페 목록 받기')
    fresh = os.path.join(WORK, 'kakao_places.new.json')
    if os.path.exists(fresh):
        os.remove(fresh)
    out = run('kakao_all.py', fresh)
    if '덜 끝남' in out or not os.path.exists(fresh):
        stop('카카오 목록을 끝까지 받지 못했다(하루 사용량을 넘었을 수 있다). 예전 목록을 그대로 둔다.')
    n_new = len(json.load(open(fresh, encoding='utf-8'))['places'])
    n_old = len(json.load(open(places, encoding='utf-8'))['places']) if os.path.exists(places) else n_new
    if n_new < n_old * 0.9:
        stop('카카오 목록이 지난번보다 10% 넘게 줄었다(%d -> %d). 쓰지 않는다.' % (n_old, n_new))
    os.replace(fresh, places)
else:
    say('3. 카카오 키가 없어서 건너뛴다.')

# 3-1. 브랜드 본사 매장 목록 다시 받기(hq_fetch/<브랜드>.py). 받기가 실패하거나 많이 줄면 지난 목록을 둔다.
say('3-1. 본사 매장 목록 다시 받기')
run(os.path.join('hq_fetch', 'run_all.py'))

# 4. 만들기 (한 번 만들어서 짝 없는 곳을 뽑고, 이름으로 물어본 뒤, 다시 만든다)
out_js, local_js = os.path.join(ROOT, 'cafes.js'), os.path.join(ROOT, 'cafes.local.js')
before = count(out_js) if os.path.exists(out_js) else (0, 0)
for f in (out_js, local_js):
    if os.path.exists(f):
        shutil.copy2(f, os.path.join(WORK, os.path.basename(f) + '.before'))
say('4. 자료 만들기')
run('build.py', WORK, out_js, *lic)
if os.path.exists(os.path.join(HERE, 'kakao_key.txt')):
    say('   짝 없는 카페를 이름으로 다시 묻기')
    run('kakao_kw.py')
    run('build.py', WORK, out_js, *lic)
# 카페마다 법정동 붙이기(새 동네가 법정동으로 센다). 브이월드 법정구역정보 zip은 작업/법정구역/에 사람이 받아 둔다.
legal_dir = os.path.join(WORK, '법정구역')
legal_zips = sorted(f for f in os.listdir(legal_dir) if f.startswith('AL_D001') and f.endswith('.zip')) if os.path.isdir(legal_dir) else []
if not legal_zips:
    stop('작업/법정구역/에 브이월드 법정구역정보 zip이 없다(새 동네가 법정동으로 센다).')
say('   카페마다 법정동 붙이기', legal_zips[-1])
run('legal_cafes.py', os.path.join(legal_dir, legal_zips[-1]), out_js, local_js)

# 5. 점검
after = count(out_js)
say('5. 점검: 카페 수 %d -> %d, 카카오 장소 번호 %d -> %d' % (before[0], after[0], before[1], after[1]))
bad = None
if before[0] and not (0.9 * before[0] <= after[0] <= 1.15 * before[0]):
    bad = '카페 수가 지난번과 10% 넘게 다르다'
elif before[1] and after[1] < 0.9 * before[1]:
    bad = '카카오와 짝지은 카페가 10% 넘게 줄었다'
if bad:
    for f in (out_js, local_js):
        b = os.path.join(WORK, os.path.basename(f) + '.before')
        if os.path.exists(b):
            shutil.copy2(b, f)
    stop(bad + '. 예전 파일로 되돌렸다.')
json.dump(state, open(STATE_PATH, 'w', encoding='utf-8'), ensure_ascii=False)
# 카페 카드의 '카페지도 정보' 탭 자료(가까운 버스정류장, 지하철역, 주차장, 지역화폐 가맹점, 건축물대장). info/*.json
say('   카페 주변 정보 만들기')
# 건축물대장: 새 카페의 건물과 열두 달 지난 건물을 한 번에 5,000곳까지(서버가 느려 한 시간쯤). 다 못 받으면 다음 달에 이어 받는다.
run('building_info.py', '--max', '5000', '--workers', '2')
run('cafe_info.py', '--fetch')
# 지도의 주차장 표시(park/*.json): 방금 받은 전국 주차장 자료를 지도 칸으로 나눈다.
run('park_tiles.py')
# 지하철 노선, 역, 아파트 단지(landmarks.js): 석 달에 한 번 OpenStreetMap에서 다시 받는다. 실패하면 옛 파일을 둔다.
ym = datetime.date.today().year * 12 + datetime.date.today().month
if ym - state.get('landmarks', 0) >= 3:
    say('   지하철, 아파트 다시 받기')
    if '갱신함' in run('fetch_landmarks.py'):
        state['landmarks'] = ym
        json.dump(state, open(STATE_PATH, 'w', encoding='utf-8'), ensure_ascii=False)

# 6. 올리기
if NO_PUSH:
    say('6. 올리지 않고 끝낸다(--no-push).')
else:
    say('6. 깃허브에 올리기')
    def git(*a):
        return subprocess.run(['git'] + list(a), cwd=ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace')
    git('add', 'cafes.js', 'info', 'landmarks.js', 'park')
    if git('diff', '--cached', '--quiet').returncode == 0:
        say('   바뀐 것이 없다.')
    else:
        c = git('commit', '-m', '카페 자료 갱신 (%s, %d곳)' % (datetime.date.today().strftime('%Y-%m'), after[0]))
        if c.returncode != 0:
            stop('커밋 실패: ' + c.stderr[-300:])
        p = git('push', 'origin', 'main')
        if p.returncode != 0:
            stop('올리기 실패: ' + p.stderr[-300:])
        say('   올렸다.')
# 7. 사람이 볼 것: 새 브랜드 후보와 키 점검 결과
say('7. 사람이 볼 것')
run('brand_candidates.py', out_js)
for line in legal_report.splitlines():
    if '새 파일' in line or '실패' in line:
        say('   법정구역:', line)
for line in key_report.splitlines():
    if '문제' in line and '문제 0개' not in line:
        say('   키를 확인해야 한다:', line)
say('==== 갱신 끝: 카페 %d곳 ====' % after[0])
