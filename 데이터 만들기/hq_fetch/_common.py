# 본사 매장 목록 받기 스크립트들이 같이 쓰는 도우미.
# 이름이 _로 시작해서 run_all.py가 브랜드로 돌리지 않는다.
# 브랜드 스크립트에서 불러 쓰는 법:
#   import os, importlib.util
#   _s = importlib.util.spec_from_file_location('_hq_common', os.path.join(os.path.dirname(os.path.abspath(__file__)), '_common.py'))
#   C = importlib.util.module_from_spec(_s); _s.loader.exec_module(C)
import csv, html, http.cookiejar, json, os, re, ssl, time, urllib.error, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(os.path.dirname(HERE), '작업')
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36'
DELAY = 0.35  # 본사 서버에 무리 가지 않게 요청마다 쉬는 시간(초)

_ctx_loose = ssl.create_default_context()
_ctx_loose.check_hostname = False
_ctx_loose.verify_mode = ssl.CERT_NONE


def _opener(ctx=None):
    cj = http.cookiejar.CookieJar()
    hs = [urllib.request.HTTPCookieProcessor(cj)]
    if ctx is not None:
        hs.append(urllib.request.HTTPSHandler(context=ctx))
    return urllib.request.build_opener(*hs)


_op = _opener()
_op_loose = _opener(_ctx_loose)


def get(url, data=None, headers=None, enc=None, js=False, delay=DELAY, timeout=40, body_on_error=False):
    """주소를 열어 글자(또는 json)를 돌려준다. 요청 뒤에는 꼭 쉰다."""
    h = {'User-Agent': UA, 'Accept-Language': 'ko-KR,ko;q=0.9'}
    if headers:
        h.update(headers)
    if isinstance(data, dict):
        data = urllib.parse.urlencode(data).encode()
    elif isinstance(data, str):
        data = data.encode()
    req = urllib.request.Request(url, data=data, headers=h)
    try:
        try:
            r = _op.open(req, timeout=timeout)
        except urllib.error.URLError as e:
            if isinstance(getattr(e, 'reason', None), ssl.SSLError):
                r = _op_loose.open(req, timeout=timeout)  # 인증서가 오래된 본사 사이트
            else:
                raise
        b = r.read()
        ct = r.headers.get('Content-Type', '')
    except urllib.error.HTTPError as e:
        if not body_on_error:
            raise
        b = e.read()
        ct = e.headers.get('Content-Type', '')
    finally:
        time.sleep(max(delay, 0.3))
    if enc is None:
        m = re.search(r'charset=([\w-]+)', ct)
        enc = m.group(1) if m else 'utf-8'
    try:
        s = b.decode(enc)
    except Exception:
        s = b.decode('cp949', 'replace')
    s = s.lstrip('﻿')
    return json.loads(s) if js else s


def clean(s):
    s = re.sub(r'<[^>]+>', ' ', str(s or ''))
    s = html.unescape(s).replace('\xa0', ' ').replace('\xad', '')
    return re.sub(r'\s+', ' ', s).strip()


def text(url, **kw):
    s = get(url, **kw)
    return clean(re.sub(r'<script.*?</script>|<style.*?</style>|<!--.*?-->', ' ', s, flags=re.S))


def uniq(rows):
    out = []
    seen = set()
    for n, a in rows:
        n, a = clean(n), clean(a)
        if n and a and (n, a) not in seen:
            seen.add((n, a))
            out.append((n, a))
    return out


def need(rows, at_least, brand=''):
    """너무 적게 받았으면 사이트가 바뀐 것으로 보고 예외를 낸다."""
    rows = uniq(rows)
    if len(rows) < at_least:
        raise RuntimeError('%s 매장이 %d곳뿐이라 사이트 모양이 바뀐 것 같음' % (brand, len(rows)))
    return rows


def pages(url_of, parse, maxp=200):
    """쪽 번호를 올려 가며 같은 목록이 나오거나 비면 멈춘다."""
    rows, prev = [], None
    for p in range(1, maxp + 1):
        r = parse(get(url_of(p)))
        if not r or r == prev:
            break
        prev = r
        rows += r
    return rows


# 아임웹 지도 게시판(제목 class="tit", 주소 class="adress")
def imweb_map(url, maxp=100):
    sep = '&' if '?' in url else ('?' if url.endswith('/') else '/?')
    return pages(lambda p: '%s%spage=%d' % (url, sep, p),
                 lambda s: re.findall(r'class="tit">(.*?)</div>.*?class="adress">(.*?)</p>', s, re.S), maxp)


# 아임웹 카드 게시판(제목 title-block, 본문 첫 줄이 주소)
def imweb_card(url, maxp=60):
    sep = '&' if '?' in url else ('?' if url.endswith('/') else '/?')

    def parse(s):
        r = []
        for m in re.finditer(r'class="title title-block">(.*?)</div>\s*(?:<div class="text text-block show_body">\s*<span>(.*?)</span>)?', s, re.S):
            t = re.sub(r'<em[^>]*>.*?</em>|<!--.*?-->', '', m.group(1), flags=re.S)
            r.append((clean(t), clean(m.group(2) or '')))
        return r
    return pages(lambda p: '%s%spage=%d' % (url, sep, p), parse, maxp)


# 아임웹 게시글마다 주소가 있는 게시판
def imweb_posts(url, addr_re, skip_re=r'오픈\s*예정|준비중|상담중', maxp=60):
    sep = '&' if '?' in url else ('?' if url.endswith('/') else '/?')
    ids = []
    for p in range(1, maxp + 1):
        s = get('%s%spage=%d' % (url, sep, p))
        new = [i for i in dict.fromkeys(re.findall(r'idx=(\d+)', s)) if i not in ids]
        if not new:
            break
        ids += new
    base = url.split('?')[0].rstrip('/')
    rows = []
    for i in ids:
        s = get('%s/?bmode=view&idx=%s&t=board' % (base, i))
        m = re.search(r'<meta property="og:title" content="(.*?)"', s)
        nm = clean(m.group(1)) if m else ''
        t = clean(re.sub(r'<script.*?</script>|<style.*?</style>|<!--.*?-->', ' ', s, flags=re.S))
        a = re.search(addr_re, t)
        if a and nm and not re.search(skip_re, nm + ' ' + a.group(1)):
            rows.append((nm, a.group(1).strip()))
    return rows


# 그누보드 mapV2 지도(titles, sub1)
def mapv2(url):
    s = get(url, timeout=60)
    return re.findall(r'class="titles[^"]*">(?:<a[^>]*>)?(.*?)(?:</a>)?</div>.{0,80}?class="sub1[^"]*">(.*?)</div>', s, re.S)


# data-name / data-address 를 쓰는 지도
def data_attr(url):
    s = get(url)
    return re.findall(r'data-name="(.*?)"\s*data-address="(.*?)"', s)


def regions():
    """작업/buildings.csv에서 (시도, 시군구) 목록과 시군구별 도로명 목록을 만든다."""
    sgg, roads = [], {}
    path = os.path.join(WORK, 'buildings.csv')
    with open(path, encoding='utf-8') as f:
        for r in csv.DictReader(f):
            k = (r['시도명'], r['시군구명'])
            if k not in roads:
                roads[k] = {}
                sgg.append(k)
            a = r['도로명주소'].split()
            rest = a[1 + len(r['시군구명'].split()):]
            if rest:
                key = rest[0] + ' ' + rest[1] if rest[0].endswith(('읍', '면')) and len(rest) > 1 else rest[0]
                roads[k][key] = roads[k].get(key, 0) + 1
    return sgg, roads


def grid_points(step=0.3):
    """작업/buildings.csv 좌표로 전국을 step도 칸으로 나눈 중심점들."""
    cells = set()
    with open(os.path.join(WORK, 'buildings.csv'), encoding='utf-8') as f:
        for r in csv.DictReader(f):
            try:
                cells.add((round(float(r['위도']) / step), round(float(r['경도']) / step)))
            except ValueError:
                pass
    return [(la * step, ln * step) for la, ln in sorted(cells)]
