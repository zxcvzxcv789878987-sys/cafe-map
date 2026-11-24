# 폐업 신고가 2명 이상 들어온 카페를 찾아 알려 준다. 지우지는 않는다(지울지는 사람이 확인하고 정한다).
# 사용법: python -I -X utf8 "데이터 만들기/gone_report.py"        (새로 생긴 것만)
#         python -I -X utf8 "데이터 만들기/gone_report.py" --all  (지금 2명 이상인 것 전부)
# 서버의 신고 목록(v2/gone)은 누구나 읽을 수 있다. 카페 이름표는 지도(index.html)와 같은 방법으로 만든다.
# 지울지 남길지는 앱의 메뉴 "받은 폐업 신고"에서 정한다(v2/gonedec). 정한 카페는 여기서 빼고, 남긴 카페는 그 뒤에 들어온 신고만 센다.
# removed.js에 이름표를 넣어도 지도에서 빠진다(예전 방법).
import sys, os, json, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DB = 'https://cafe-map-486ae-default-rtdb.firebaseio.com'
SEEN = os.path.join(HERE, '작업', 'gone_seen.json')
NEED = 2
M = 0xffffffff


def imul(a, b):
    return ((a & M) * (b & M)) & M


def hash36(text):
    """index.html의 hash36과 같은 값을 낸다(카페 이름표)."""
    h1, h2 = 0xdeadbeef, 0x41c6ce57
    raw = text.encode('utf-16-le')
    for k in range(0, len(raw), 2):
        ch = raw[k] | (raw[k + 1] << 8)
        h1 = imul(h1 ^ ch, 2654435761)
        h2 = imul(h2 ^ ch, 1597334677)
    h1 = imul(h1 ^ (h1 >> 16), 2246822507) ^ imul(h2 ^ (h2 >> 13), 3266489909)
    h2 = imul(h2 ^ (h2 >> 16), 2246822507) ^ imul(h1 ^ (h1 >> 13), 3266489909)
    n = 4294967296 * (h2 & 2097151) + (h1 & M)
    digits, out = '0123456789abcdefghijklmnopqrstuvwxyz', ''
    while n:
        n, r = divmod(n, 36)
        out = digits[r] + out
    return out or '0'


def load_cafes():
    s = open(os.path.join(ROOT, 'cafes.js'), encoding='utf-8').read()
    d = json.loads(s[len('window.CAFES='):-1])
    by = {}
    for i, name in enumerate(d['name']):
        g = d['dong'][d['dongOf'][i]][1]
        sg, sido = d['sgg'][g][0], d['sido'][d['sgg'][g][1]]
        addr = (sido if sg == sido else sido + ' ' + sg) + ' ' + d['road'][i]
        by[hash36(name + '|' + addr)] = (name, addr)
    return by


def main():
    try:
        with urllib.request.urlopen(DB + '/v2/gone.json', timeout=30) as r:
            gone = json.load(r) or {}
    except Exception as e:
        print('신고 목록을 받지 못했다:', e)
        return 1
    try:
        with urllib.request.urlopen(DB + '/v2/gonedec.json', timeout=30) as r:
            dec = json.load(r) or {}
    except Exception:
        dec = {}   # 규칙을 게시하기 전에는 읽을 수 없다
    hot = {}
    for k, v in gone.items():
        if not isinstance(v, dict):
            continue
        d = dec.get(k) or {}
        if d.get('d') == 1:
            continue
        after = d.get('t', 0) if d.get('d') == 0 else 0
        n = sum(1 for x in v.values() if isinstance(x, dict) and x.get('t', 0) > after)
        if n >= NEED:
            hot[k] = n
    seen = json.load(open(SEEN, encoding='utf-8')) if os.path.exists(SEEN) else {}
    show = hot if '--all' in sys.argv else {k: n for k, n in hot.items() if seen.get(k, 0) < n}
    print('폐업 신고가 있는 카페 %d곳, 그중 %d명 이상 %d곳' % (len(gone), NEED, len(hot)))
    if not show:
        print('새로 알릴 신고 없음')
        return 0
    cafes = load_cafes()
    print('확인이 필요한 카페:')
    for k, n in sorted(show.items(), key=lambda x: -x[1]):
        name, addr = cafes.get(k, ('(지금 목록에 없는 카페)', ''))
        print('  %d명 | %s | %s | 이름표 %s' % (n, name, addr, k))
    if '--all' not in sys.argv:
        os.makedirs(os.path.dirname(SEEN), exist_ok=True)
        seen.update(show)
        json.dump(seen, open(SEEN, 'w', encoding='utf-8'), ensure_ascii=False)
    return 0


if __name__ == '__main__':
    sys.exit(main())
