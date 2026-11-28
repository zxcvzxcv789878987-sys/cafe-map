# 본사 매장 목록 받기 스크립트들이 같이 쓰는 도우미.
# 이름이 _로 시작해서 run_all.py가 브랜드로 돌리지 않는다.
# 표준 라이브러리만 쓴다. 요청 사이는 늘 0.35초 이상 쉰다.
import html, json, re, ssl, time, urllib.parse, urllib.request

UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/120.0 Safari/537.36')
GAP = 0.35
_last = [0.0]

# 주소처럼 보이는 줄(시도 이름으로 시작)
REGION = (r'^(서울|경기|인천|부산|대구|대전|광주|울산|세종|강원|충[청남북]|전[라남북]|전북|'
          r'경[상남북]|경남|경북|충남|충북|전남|제주)\S*\s')
# 매장이 아닌 줄(본사 사무실, 폐점, 오픈 예정, 휴점, 표 머리)
NOT_STORE = re.compile(r'본사$|폐점|예정|매출|\[휴점\]|^매장명$|^지점명$|coming soon', re.I)


def _wait():
    d = time.time() - _last[0]
    if d < GAP:
        time.sleep(GAP - d)
    _last[0] = time.time()


def _old_tls_opener():
    # 오래된 암호 설정을 쓰는 본사 서버용. 인증서 확인은 그대로 한다.
    ctx = ssl.create_default_context()
    ctx.set_ciphers('DEFAULT:@SECLEVEL=1')
    return urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx))


def get(url, data=None, headers=None, enc=None, timeout=40, old_tls=False):
    """주소를 받아 글자로 돌려준다. data가 dict면 POST로 보낸다."""
    if isinstance(data, dict):
        data = urllib.parse.urlencode(data).encode()
    hd = {'User-Agent': UA}
    hd.update(headers or {})
    opener = _old_tls_opener() if old_tls else urllib.request.build_opener()
    err = None
    for _ in range(3):
        _wait()
        try:
            b = opener.open(urllib.request.Request(url, data=data, headers=hd),
                            timeout=timeout).read()
            if enc:
                return b.decode(enc, 'replace')
            t = b.decode('utf-8', 'replace')
            if t.count('�') > 30:
                t = b.decode('cp949', 'replace')
            return t
        except Exception as e:
            err = e
            time.sleep(2)
    raise err


def get_json(url, data=None, headers=None):
    return json.loads(get(url, data, headers))


def txt(s):
    """태그를 빼고 공백을 하나로 줄인다."""
    return ' '.join(html.unescape(re.sub(r'<[^>]+>', ' ', str(s or ''))).split())


def lines(h):
    """화면 글자를 줄 목록으로. 스크립트, 스타일, 주석은 뺀다."""
    t = re.sub(r'<script.*?</script>|<style.*?</style>|<!--.*?-->', '', h, flags=re.S)
    t = html.unescape(re.sub(r'<[^>]+>', '\n', t))
    return [x.strip() for x in t.split('\n') if x.strip()]


def jsvar(h, name):
    """화면 안 스크립트의 'var 이름 = [...]' 값을 읽는다."""
    i = h.index(name)
    j = h.index('=', i) + 1
    while h[j] in ' \n\t\r':
        j += 1
    return json.JSONDecoder().raw_decode(h, j)[0]


def clean(rows):
    """이름, 주소를 다듬고 매장이 아닌 줄과 겹친 줄을 뺀다."""
    out, seen = [], set()
    for n, a in rows:
        n, a = txt(n), txt(a)
        if not n or not a or NOT_STORE.search(n):
            continue
        if (n, a) in seen:
            continue
        seen.add((n, a))
        out.append((n, a))
    if not out:
        raise RuntimeError('매장을 하나도 못 읽음(화면 모양이 바뀌었을 수 있음)')
    return out


def pages(make_url, pat, start=1, stop=300, data=None):
    """쪽을 넘기며 정규식 두 칸(이름, 주소)을 모은다. 새 줄이 안 나오면 멈춘다."""
    rows = []
    for p in range(start, stop):
        try:
            h = get(make_url(p), data(p) if data else None)
        except Exception:
            if p == start:
                raise
            break   # 마지막 쪽 다음은 404를 주는 곳이 있다
        new = [(txt(a), txt(b)) for a, b in re.findall(pat, h, re.S)]
        new = [x for x in new if x not in rows]
        if not new:
            break
        rows += new
    return rows


def imweb(site, path, prefix=None, stop=200):
    """아임웹 지도 게시판. 'text' 표시 다음 줄이 이름, 그다음 줄이 주소.
    prefix를 주면 그 말로 시작하는 줄을 이름으로 본다."""
    h = get(site + path)
    q = re.findall(r'href="(' + re.escape(path.rstrip('/')) + r'/?\?q=[^"]*?)page=\d+"', h)
    base = html.unescape(q[0]) if q else path + ('&' if '?' in path else '?')
    rows = []
    for p in range(1, stop):
        L = lines(get(site + base + 'page=%d' % p))
        if prefix:
            r = [(x, L[i + 1]) for i, x in enumerate(L[:-1])
                 if x.startswith(prefix) and re.search(r'\d', L[i + 1]) and not L[i + 1].startswith(prefix)]
        else:
            r = [(L[i + 1], L[i + 2]) for i, x in enumerate(L[:-2])
                 if x == 'text' and re.search(r'\d', L[i + 2])]
        new = [x for x in r if x not in rows]
        if not new:
            break
        rows += new
    return rows
