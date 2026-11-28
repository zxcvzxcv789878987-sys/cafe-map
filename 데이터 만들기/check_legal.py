# 브이월드에 새 법정구역 파일(전국 법정구역정보 SHP, 전체데이터)이 나왔는지 본다. 받기는 로그인이 필요해서 사람이 한다.
# 브이월드 목록 화면(로그인 없이 보임)의 가장 늦은 "전체데이터 기준일"과 작업/법정구역/의 zip 날짜를 견준다.
# 실패해도 끝 코드는 0이다. 결과는 마지막 줄에 적는다.
import os, re, html, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
PAGE = ('https://www.vworld.kr/dtmk/dtmk_ntads_s002.do?svcCde=NA&dsId=21&pageIndex=1&pageSize=10&pageUnit=10'
        '&dataSetSeq=21&datPageIndex=1&datPageSize=10&fileGbnCd=AL&formatSelect=SHP')


def main():
    d = os.path.join(HERE, '작업', '법정구역')
    have = sorted(re.findall(r'AL_D001_\d+_(\d{8})\.zip', ' '.join(os.listdir(d)))) if os.path.isdir(d) else []
    have = have[-1] if have else '00000000'
    try:
        t = urllib.request.urlopen(urllib.request.Request(PAGE, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126'}),
                                   timeout=60).read().decode('utf-8', 'replace')
    except Exception as e:
        print('법정구역 점검 실패(브이월드 화면을 못 읽음):', type(e).__name__)
        return
    text = re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', t)))
    dates = re.findall(r'전국 법정구역정보 .{0,40}?전체데이터 기준일 (\d{4})-(\d\d)-(\d\d)', text)
    if not dates:
        print('법정구역 점검 실패(브이월드 화면 모양이 바뀐 것 같다)')
        return
    newest = max(''.join(x) for x in dates)
    if newest > have:
        print('법정구역 새 파일 있음: 기준일 %s (가진 것 %s). 브이월드에서 SHP 전국 법정구역정보를 받아 작업/법정구역에 넣어야 한다' % (newest, have))
    else:
        print('법정구역 최신: 기준일 %s' % newest)


if __name__ == '__main__':
    main()
