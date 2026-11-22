# 상가정보 zip에서 카페만 뽑아 cafes_raw.csv로 저장하고, 상호명 빈도를 top_names.txt로 남긴다.
import zipfile, sys, io, csv, collections

zpath, outdir = sys.argv[1], sys.argv[2]
z = zipfile.ZipFile(zpath)
keep = ['상가업소번호', '상호명', '지점명', '상권업종소분류명', '시도명', '시군구명', '행정동명',
        '도로명주소', '층정보', '경도', '위도']
cnt = collections.Counter()
cat = collections.Counter()
total = 0
with open(f'{outdir}/cafes_raw.csv', 'w', encoding='utf-8', newline='') as out:
    w = csv.writer(out)
    w.writerow(keep)
    for n in z.namelist():
        if not n.endswith('.csv'):
            continue
        f = io.TextIOWrapper(z.open(n), encoding='utf-8-sig')
        r = csv.reader(f)
        h = next(r)
        idx = {k: h.index(k) for k in keep}
        i_mid = h.index('상권업종중분류명')
        for row in r:
            if row[i_mid].strip() == '비알코올' or '카페' in row[idx['상권업종소분류명']]:
                cat[(row[i_mid].strip(), row[idx['상권업종소분류명']].strip())] += 1
            if row[idx['상권업종소분류명']].strip() != '카페':
                continue
            total += 1
            w.writerow([row[idx[k]].strip() for k in keep])
            cnt[row[idx['상호명']].replace(' ', '')] += 1

with open(f'{outdir}/top_names.txt', 'w', encoding='utf-8') as o:
    o.write(f'total cafes {total}\n')
    for k, v in cat.most_common():
        o.write(f'CAT {k} {v}\n')
    for k, v in cnt.most_common(400):
        o.write(f'{v}\t{k}\n')
