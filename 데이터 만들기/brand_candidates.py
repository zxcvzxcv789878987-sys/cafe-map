# 브랜드로 안 잡혔는데 같은 이름(지점 이름을 뗀 앞부분)이 여러 곳인 가게를 센다.
# 흔한 가게 이름(정다방 같은 것)을 빼려고, 지점 이름("OO 강남점")이 붙은 곳이 5곳 넘는 이름만 센다.
# 새 브랜드를 brands.py에 넣을지 사람이 보고 정한다. 고치지는 않는다.
# 사용법: python brand_candidates.py <cafes.js> [최소 곳 수, 기본 10]
import json, re, sys, collections

GENERIC = {'카페', '커피', '까페', 'cafe', 'coffee', '커피숍', '다방', '베이커리', '제과', '제과점', '빵집', '디저트',
           '디저트카페', '커피전문점', '테이크아웃', '스터디카페', '북카페', '키즈카페', '애견카페', '무인카페', '셀프카페'}


def head(name):
    s = re.sub(r'\([^)]*\)', ' ', name.lower())
    s = re.sub(r'\s+\S*점$', '', s.strip())            # "OO커피 강남점"의 "강남점"
    s = re.sub(r'(\S{2,}?)(본|직영|\S{1,6})점$', r'\1', s) if ' ' not in s and len(s) > 6 and s.endswith('점') else s
    return re.sub(r'[^0-9a-z가-힣]', '', s)


def main():
    src = open(sys.argv[1], encoding='utf-8').read()
    d = json.loads(src[src.index('=') + 1:src.rindex(';')])
    least = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    c, br, ex = collections.Counter(), collections.Counter(), {}
    for nm, b in zip(d['name'], d['brand']):
        if b >= 0:
            continue
        h = head(nm)
        if len(h) < 2 or h in GENERIC:
            continue
        c[h] += 1
        if re.search(r'\S점\)?$', nm.strip()) and not nm.strip().endswith(('다방점', '본점')) and head(nm) != re.sub(r'[^0-9a-z가-힣]', '', nm.lower()):
            br[h] += 1
            ex.setdefault(h, nm)
    rows = [(n, h) for h, n in c.items() if n >= least and br[h] >= 5]
    rows.sort(reverse=True)
    print('새 브랜드 후보(브랜드 아님, 같은 이름 %d곳 이상, 지점 이름 붙은 곳 5곳 넘음) %d개' % (least, len(rows)))
    lines = ['  %d곳(지점 이름 %d) %s (예: %s)' % (n, br[h], h, ex[h]) for n, h in rows]
    for l in lines[:10]:          # 갱신 기록에는 위 10개만, 전체는 작업/brand_candidates.txt
        print(l)
    import os
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), '작업', 'brand_candidates.txt')
    open(out, 'w', encoding='utf-8').write(''.join(l + chr(10) for l in lines))


if __name__ == '__main__':
    main()
