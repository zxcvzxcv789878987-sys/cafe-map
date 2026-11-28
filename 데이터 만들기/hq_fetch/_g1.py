# 그룹1 본사 목록 스크립트들이 같이 쓰는 도구(표준 라이브러리만).
# run_all.py는 _로 시작하는 파일을 건너뛴다.
import html, json, re, time, urllib.parse, urllib.request, http.cookiejar

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36"
_op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
_last = [0.0]
GAP = 0.5  # 본사 서버에 무리 가지 않게 요청 사이 쉬는 초


def get(url, data=None, headers=None):
    """글로 받는다. data가 있으면 POST(dict 또는 str)."""
    wait = GAP - (time.time() - _last[0])
    if wait > 0:
        time.sleep(wait)
    h = {"User-Agent": UA, "Accept": "*/*", "Accept-Language": "ko-KR,ko;q=0.9"}
    if headers:
        h.update(headers)
    body = None
    if data is not None:
        body = data.encode() if isinstance(data, str) else urllib.parse.urlencode(data).encode()
        h.setdefault("Content-Type", "application/x-www-form-urlencoded; charset=UTF-8")
    req = urllib.request.Request(url, data=body, headers=h)
    err = None
    for i in range(3):
        try:
            b = _op.open(req, timeout=40).read()
            break
        except Exception as e:
            err = e
            time.sleep(2)
    else:
        raise err
    _last[0] = time.time()
    for enc in ("utf-8", "cp949"):
        try:
            return b.decode(enc)
        except UnicodeDecodeError:
            pass
    return b.decode("utf-8", "replace")


def clean(s):
    s = html.unescape(re.sub(r"<[^>]+>", " ", s or ""))
    return re.sub(r"\s+", " ", s).strip()


def flat(t):
    """태그를 |로 바꾼 한 줄 글."""
    x = re.sub(r"<script.*?</script>|<style.*?</style>|<svg.*?</svg>", "", t, flags=re.S)
    x = re.sub(r"<[^>]+>", "|", x)
    x = html.unescape(re.sub(r"\s+", " ", x))
    return re.sub(r"(\| ?)+", "|", x)


def done(rows, least=1):
    """정리하고 너무 적으면 예외."""
    out = []
    for n, a in rows:
        n, a = clean(n), clean(a)
        if n and a and (n, a) not in out:
            out.append((n, a))
    if len(out) < least:
        raise RuntimeError("매장을 %d곳밖에 못 읽음(화면 구조가 바뀌었을 수 있음)" % len(out))
    return out


SKIP = r"오픈\s*예정|오픈\s*준비|준비중|폐점|휴점"


def imweb_list(base, board, ref):
    """아임웹 지도 목록 위젯(/ajax/get_map_list.cm)을 쪽마다 읽는다."""
    rows, seen = [], set()
    for p in range(1, 200):
        t = get(base + "/ajax/get_map_list.cm",
                  data={"board_code": board, "search": "", "search_mod": "all", "page": p, "sort": "TIME", "status": ""},
                  headers={"Referer": ref})
        items = re.findall(r'id="list_(\d+)".*?<div class="tit">(.*?)</div>.*?<p class="adress">(.*?)</p>', t, re.S)
        new = [i for i in items if i[0] not in seen]
        if not new:
            break
        for i, n, a in new:
            seen.add(i)
            if not re.search(SKIP, clean(n)):
                rows.append((n, a))
    return rows


def imweb_boards(page_html):
    return sorted(set(re.findall(r"_map_view_(b20[0-9]{6}[0-9a-f]{12,14})", page_html)))


def g5_array(t):
    """그누보드 매장 스킨의 var array = [...] 를 읽는다."""
    m = re.search(r"var array = (\[.*?\]);\s*\n", t, re.S)
    if not m:
        raise RuntimeError("매장 자료(var array)를 못 찾음")
    return json.loads(m.group(1))
