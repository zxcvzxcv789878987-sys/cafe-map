# 지하철 노선, 역, 아파트 단지를 OpenStreetMap(Overpass API, 키 없음)에서 다시 받아 landmarks.js를 새로 만든다.
# 받은 원본은 작업/osm/에 둔다. 받기가 실패하거나 지난번보다 10% 넘게 줄면 옛 landmarks.js를 그대로 둔다.
# 실패해도 끝 코드는 0이다(매달 갱신을 멈추지 않는다). 결과는 마지막 줄에 적는다.
# 사용법: python -I -X utf8 fetch_landmarks.py
import os, sys, json, time, shutil, subprocess, urllib.request, urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OSM = os.path.join(HERE, '작업', 'osm')
os.makedirs(OSM, exist_ok=True)
SERVERS = ['https://overpass-api.de/api/interpreter', 'https://overpass.kumi.systems/api/interpreter']
KR = 'area["ISO3166-1"="KR"][admin_level=2]->.kr;'
Q = {
    'geom': '[out:json][timeout:240];' + KR + '''(
  relation["type"="route"]["route"~"^(subway|light_rail|monorail)$"]["colour"](area.kr);
  relation["type"="route"]["route"="train"]["colour"]["network"~"수도권 전철|부산 도시철도"](area.kr);
  relation["type"="route"]["route"="train"]["colour"]["ref"="대경"](area.kr);
)->.r;
.r out body;
way(r.r);
out geom;''',
    'stations': '[out:json][timeout:120];' + KR + 'node["railway"~"^(station|halt)$"](area.kr);out;',
    'apt': '[out:json][timeout:300];' + KR + '''(
  way["landuse"="residential"]["name"](area.kr);
  relation["landuse"="residential"]["name"](area.kr);
  way["residential"="apartments"]["name"](area.kr);
);
out center tags;''',
}


def n_elements(path):
    try:
        return len(json.load(open(path, encoding='utf-8'))['elements'])
    except Exception:
        return 0


def fetch(name):
    path = os.path.join(OSM, name + '.json')
    tmp = path + '.new'
    body = urllib.parse.urlencode({'data': Q[name]}).encode()
    last = ''
    for url in SERVERS:
        for t in range(2):
            try:
                req = urllib.request.Request(url, data=body, headers={'User-Agent': 'cafe-map/1.0'})
                with urllib.request.urlopen(req, timeout=330) as r, open(tmp, 'wb') as f:
                    shutil.copyfileobj(r, f)
                n = n_elements(tmp)
                if n:
                    return tmp, n
                last = '빈 답'
            except Exception as e:
                last = type(e).__name__ + ' ' + str(e)[:80]
            time.sleep(30)
    raise RuntimeError(name + ' 받기 실패: ' + last)


def main():
    got = {}
    try:
        for name in Q:
            tmp, n = fetch(name)
            old = n_elements(os.path.join(OSM, name + '.json'))
            print('%s: %d개 (지난번 %d개)' % (name, n, old), flush=True)
            if old and n < old * 0.9:
                raise RuntimeError('%s가 지난번보다 10%% 넘게 줄었다' % name)
            got[name] = tmp
            time.sleep(10)      # 공용 서버라 쉬엄쉬엄
    except Exception as e:
        print('지하철, 아파트 갱신 안 함(옛 파일 그대로):', e)
        return
    out = os.path.join(ROOT, 'landmarks.js')
    new = out + '.new'
    p = subprocess.run([sys.executable, '-I', '-X', 'utf8', os.path.join(HERE, 'build_landmarks.py'),
                        got['geom'], got['stations'], got['apt'], new], capture_output=True, text=True, encoding='utf-8', errors='replace')
    if p.returncode != 0 or not os.path.exists(new):
        print('지하철, 아파트 갱신 안 함(만들기 실패):', (p.stderr or '')[-300:])
        return
    a, b = os.path.getsize(out) if os.path.exists(out) else 0, os.path.getsize(new)
    if a and b < a * 0.9:
        os.remove(new)
        print('지하철, 아파트 갱신 안 함: 새 파일이 10%% 넘게 작다(%d -> %d)' % (a, b))
        return
    os.replace(new, out)
    for name, tmp in got.items():
        os.replace(tmp, os.path.join(OSM, name + '.json'))
    print('지하철, 아파트 갱신함: landmarks.js %dKB -> %dKB' % (a // 1024, b // 1024))


if __name__ == '__main__':
    main()
