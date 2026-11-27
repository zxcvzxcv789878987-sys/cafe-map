# 브랜드 로고를 공식 출처(공식 앱 아이콘, 공식 사이트 아이콘이나 로고)에서 한 번 받아 logos/ 폴더에 작은 그림으로 둔다.
# (사용자 2026-11-27: 그때그때 남의 사이트에서 불러오면 흐리거나 바뀌어서 틀린 그림이 나온다 → 받아 두기)
# 사용법: python -X utf8 logos.py <목록.json>
#   목록.json: [{"name": "스타벅스", "url": "https://...", "full": true}, ...]
#     full: 앱 아이콘처럼 네모 가득 색이 찬 그림(동그라미에 꽉 채운다). 아니면 투명 바탕 로고(가장자리를 잘라 안쪽에 넣는다).
#     box: 단색 바탕 위 로고(사이트 대표 그림 등). 로고 둘레만 잘라 그 바탕색으로 꽉 채운다.
#     crop: [x0, y0, x1, y1] 먼저 잘라 낼 칸(픽셀)
#     file: url 대신 내 컴퓨터의 그림(사용자가 캡처해 준 것 등)
# 결과: logos/<이름의 해시>.webp(꽉 채우는 그림은 -f.webp), logos/index.json(브랜드 이름 → 파일)
import hashlib, io, json, os, sys, urllib.request
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '작업', 'pylib'))
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'logos')
SIZE = 192
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36'


def fetch(u):
    import urllib.parse
    pr = urllib.parse.urlsplit(u)
    u = urllib.parse.urlunsplit((pr.scheme, pr.netloc.encode('idna').decode(), urllib.parse.quote(pr.path, safe='/%~'), pr.query, pr.fragment))
    req = urllib.request.Request(u, headers={'User-Agent': UA, 'Accept': 'image/*,*/*'})
    return urllib.request.urlopen(req, timeout=30).read()


def largest(im):
    # .ico에는 크기가 여러 개 들어 있다. 가장 큰 것을 쓴다.
    if getattr(im, 'format', '') == 'ICO' and hasattr(im, 'ico'):
        sizes = sorted(im.ico.sizes(), key=lambda s: s[0] * s[1])
        if sizes:
            im.size = sizes[-1]
            im.load()
    return im


def make(raw, full, box=False, crop=None):
    im = largest(Image.open(io.BytesIO(raw)))
    im = im.convert('RGBA')
    if crop:
        im = im.crop(tuple(crop))   # 큰 그림에서 로고 둘레만 먼저 잘라 낸다(바탕에 무늬가 있어 저절로 못 자를 때)
    src = min(im.size)
    if box:
        # 단색 바탕 위에 로고가 있는 그림(사이트 대표 그림 등): 바탕색은 그대로 두고 로고 둘레만 잘라 네모 가운데에 넣는다(동그라미에 꽉 채움).
        from PIL import ImageChops
        rgb = im.convert('RGB')
        bgc = rgb.getpixel((2, 2))
        diff = ImageChops.difference(rgb, Image.new('RGB', rgb.size, bgc)).convert('L').point(lambda v: 255 if v > 40 else 0)
        bb = diff.getbbox() or (0, 0) + rgb.size
        im = rgb.crop(bb)
        w, h = im.size
        s = int(max(w, h) / .74)        # 동그라미 안에 다 들어가게 둘레를 넉넉히
        sq = Image.new('RGB', (s, s), bgc)
        sq.paste(im, ((s - w) // 2, (s - h) // 2))
        im = sq.convert('RGBA')
        src = max(w, h)
    elif full:
        w, h = im.size
        s = min(w, h)
        im = im.crop(((w - s) // 2, (h - s) // 2, (w - s) // 2 + s, (h - s) // 2 + s))
    else:
        # 투명하거나 흰 가장자리를 잘라 내고 네모로 맞춘다
        bg = Image.new('RGBA', im.size, (255, 255, 255, 0))
        alpha = im.split()[3]
        box = alpha.point(lambda a: 255 if a > 8 else 0).getbbox()
        if box and box != (0, 0) + im.size:
            im = im.crop(box)
        else:
            rgb = im.convert('RGB')
            white = Image.new('RGB', rgb.size, (255, 255, 255))
            from PIL import ImageChops
            diff = ImageChops.difference(rgb, white).convert('L').point(lambda v: 255 if v > 12 else 0)
            box = diff.getbbox()
            if box:
                im = im.crop(box)
        w, h = im.size
        s = max(w, h)
        sq = Image.new('RGBA', (s, s), (255, 255, 255, 0))
        sq.paste(im, ((s - w) // 2, (s - h) // 2))
        im = sq
    if im.size[0] != SIZE:
        im = im.resize((SIZE, SIZE), Image.LANCZOS)
    return im, src


def main(path):
    os.makedirs(OUT, exist_ok=True)
    idx_path = os.path.join(OUT, 'index.json')
    idx = json.load(open(idx_path, encoding='utf-8')) if os.path.exists(idx_path) else {}
    items = json.load(open(path, encoding='utf-8'))
    for it in items:
        nm = it['name']
        try:
            raw = open(it['file'], 'rb').read() if it.get('file') else fetch(it['url'])
            im, src = make(raw, it.get('full') or it.get('box'), it.get('box'), it.get('crop'))
        except Exception as e:
            print('실패', nm, str(e)[:100])
            continue
        h = hashlib.md5(nm.encode('utf-8')).hexdigest()[:10]
        fn = h + ('-f' if (it.get('full') or it.get('box')) else '') + '.webp'
        for old in (h + '.webp', h + '-f.webp'):
            if old != fn and os.path.exists(os.path.join(OUT, old)):
                os.remove(os.path.join(OUT, old))
        im.save(os.path.join(OUT, fn), 'WEBP', quality=88, method=6)
        idx[nm] = {'file': 'logos/' + fn, 'src': it.get('url') or 'file', 'px': src}
        print('저장', nm, fn, '원본', src, 'px')
    json.dump(dict(sorted(idx.items())), open(idx_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    apply(idx)


def apply(idx):
    # index.html의 BRAND_ICON 표를 logos/index.json으로 다시 쓴다.
    p = os.path.join(ROOT, 'index.html')
    s = open(p, encoding='utf-8').read()
    a = s.index('  var BRAND_ICON = {')
    b = s.index('  };', a) + len('  };')
    rows = ',\n'.join("    '%s': '%s'" % (k, v['file']) for k, v in sorted(idx.items()))
    s = s[:a] + '  var BRAND_ICON = {\n' + rows + '\n  };' + s[b:]
    open(p, 'w', encoding='utf-8').write(s)
    print('index.html 로고 표', len(idx), '곳')


if __name__ == '__main__':
    if sys.argv[1] == '--apply':
        apply(json.load(open(os.path.join(OUT, 'index.json'), encoding='utf-8')))
    else:
        main(sys.argv[1])
