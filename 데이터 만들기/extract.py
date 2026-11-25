# 상가정보 zip에서 카페만 뽑아 cafes_raw.csv로 저장하고, 상호명 빈도를 top_names.txt로 남긴다.
# 업종이 빵/도넛인 가게는 bread_raw.csv로 따로 저장한다. build.py가 그중 카카오맵이 카페로 분류한 곳만 카페로 더한다.
# 그리고 모든 업종의 가게에서 건물마다 한 줄씩(도로명주소, 시도, 시군구, 행정동, 좌표) 뽑아 buildings.csv로 저장한다.
# 인허가 자료에는 행정동과 위경도가 없어서, 최근 문 연 카페를 인허가 자료에서 더할 때 이 표에서 같은 건물을 찾아 붙인다.
import zipfile, sys, io, csv, collections

zpath, outdir = sys.argv[1], sys.argv[2]
z = zipfile.ZipFile(zpath)
# 건물관리번호는 정부가 건물마다 붙인 번호다. 행정안전부의 건물 도형, 출입구 좌표와 주소 글자를 견주지 않고 이 번호로 맞춘다.
# 동정보, 호정보는 한 주소에 건물이 여러 동인 단지에서 어느 동인지 가릴 때 쓴다.
keep = ['상가업소번호', '상호명', '지점명', '상권업종소분류명', '시도명', '시군구명', '행정동명',
        '도로명주소', '층정보', '경도', '위도', '건물관리번호', '건물명', '동정보', '호정보', '법정동명', '지번주소']
cnt = collections.Counter()
cat = collections.Counter()
total = 0
bkeep = ['도로명주소', '시도명', '시군구명', '행정동명', '경도', '위도']
seen = set()
with open(f'{outdir}/cafes_raw.csv', 'w', encoding='utf-8', newline='') as out, open(f'{outdir}/buildings.csv', 'w', encoding='utf-8', newline='') as bout, open(f'{outdir}/bread_raw.csv', 'w', encoding='utf-8', newline='') as brout:
    w = csv.writer(out)
    w.writerow(keep)
    brw = csv.writer(brout)
    brw.writerow(keep)
    bw = csv.writer(bout)
    bw.writerow(bkeep)
    for n in z.namelist():
        if not n.endswith('.csv'):
            continue
        f = io.TextIOWrapper(z.open(n), encoding='utf-8-sig')
        r = csv.reader(f)
        h = next(r)
        idx = {k: h.index(k) for k in keep}
        i_mid = h.index('상권업종중분류명')
        bidx = [h.index(k) for k in bkeep]
        i_bld = h.index('건물관리번호')
        for row in r:
            if row[i_bld] not in seen and row[bidx[0]].strip() and row[bidx[4]].strip():
                seen.add(row[i_bld])
                bw.writerow([row[i].strip() for i in bidx])
            if row[i_mid].strip() == '비알코올' or '카페' in row[idx['상권업종소분류명']]:
                cat[(row[i_mid].strip(), row[idx['상권업종소분류명']].strip())] += 1
            if row[idx['상권업종소분류명']].strip() == '빵/도넛':
                brw.writerow([row[idx[k]].strip() for k in keep])
                continue
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
