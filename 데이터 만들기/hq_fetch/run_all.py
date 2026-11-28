# 본사 매장 목록 매달 다시 받기.
# hq_fetch/<브랜드>.py 마다 SOURCE(출처 주소)와 fetch()를 둔다.
# fetch()는 [(매장명, 도로명주소), ...]를 돌려준다. 실패하면 예외를 낸다.
# 여기서 작업/hq/<브랜드>.csv를 쓴다. 받기가 실패하거나 매장 수가
# 지난 목록보다 20% 넘게 줄면 지난 목록을 그대로 두고 보고에 적는다.
# 사용법: python -I -X utf8 hq_fetch/run_all.py [브랜드 ...]
import csv, datetime, importlib.util, os, sys, traceback

HERE = os.path.dirname(os.path.abspath(__file__))
HQ = os.path.join(os.path.dirname(HERE), '작업', 'hq')


def old_count(path):
    if not os.path.exists(path):
        return 0
    with open(path, encoding='utf-8-sig') as f:
        return max(sum(1 for _ in f) - 1, 0)


def run(brand):
    spec = importlib.util.spec_from_file_location('hq_' + brand, os.path.join(HERE, brand + '.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    out = os.path.join(HQ, brand + '.csv')
    before = old_count(out)
    try:
        rows = [(n.strip(), a.strip()) for n, a in mod.fetch() if n and a and n.strip() and a.strip()]
    except Exception as e:
        return '%s: 받기 실패, 지난 목록 %d곳 그대로 (%s)' % (brand, before, str(e)[:120])
    rows = list(dict.fromkeys(rows))
    if not rows or (before and len(rows) < before * 0.8):
        return '%s: %d곳만 받음, 지난 %d곳보다 많이 줄어 그대로 둠' % (brand, len(rows), before)
    today = datetime.date.today().isoformat()
    tmp = out + '.tmp'
    with open(tmp, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(['매장명', '도로명주소', '출처', '받은날'])
        for n, a in rows:
            w.writerow([n, a, mod.SOURCE, today])
    os.replace(tmp, out)
    return '%s: %d곳 (지난 %d곳)' % (brand, len(rows), before)


def main():
    names = sys.argv[1:] or sorted(f[:-3] for f in os.listdir(HERE)
                                   if f.endswith('.py') and f != 'run_all.py' and not f.startswith('_'))
    bad = 0
    for b in names:
        try:
            msg = run(b)
        except Exception:
            msg = '%s: 스크립트 오류 %s' % (b, traceback.format_exc(limit=1).strip().splitlines()[-1])
        if '그대로' in msg or '오류' in msg:
            bad += 1
        print(msg, flush=True)
    print('본사 목록 %d개 중 문제 %d개' % (len(names), bad))


if __name__ == '__main__':
    main()
