# 매달 갱신 처음에 키마다 한 번씩 물어서 살아 있는지 본다. 키 값은 출력하지 않는다.
# 결과: 정상 / 만료 또는 등록 안 됨 / 하루 한도 / 서버 오류. 실패해도 갱신을 멈추지는 않는다(refresh.py가 보고에 적는다).
import os, json, urllib.request, urllib.parse, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))


def read(name):
    p = os.path.join(HERE, name)
    return open(p, encoding='utf-8').read().strip() if os.path.exists(p) else None


def judge(code, text):
    t = (text or '').upper()
    if code == 429 or 'LIMITED_NUMBER' in t or 'EXCEEDS' in t or 'QUOTA' in t:
        return '하루 한도'
    if code in (401, 403) or 'SERVICE_KEY_IS_NOT_REGISTERED' in t or 'EXPIRED' in t or 'UNREGISTERED' in t \
            or 'INVALID' in t and 'KEY' in t or 'SERVICE ACCESS DENIED' in t:
        return '만료 또는 등록 안 됨'
    if code != 200:
        return '서버 오류(%s)' % code
    return '정상'


def ask(url, headers=None):
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, headers=dict({'User-Agent': 'Mozilla/5.0'}, **(headers or {}))), timeout=30)
        return r.status, r.read(3000).decode('utf-8', 'replace')
    except urllib.error.HTTPError as e:
        return e.code, e.read(3000).decode('utf-8', 'replace')
    except Exception as e:
        return 0, type(e).__name__


def main():
    out = []
    dg = read('datago_key.txt')
    if dg:
        tests = [
            ('공공데이터 주차장', 'http://api.data.go.kr/openapi/tn_pubr_prkplce_info_api', {'pageNo': 1, 'numOfRows': 1, 'type': 'json'}),
            ('공공데이터 지역화폐', 'https://apis.data.go.kr/B190001/mobileFranchisesV4/mobileV4', {'page': 1, 'perPage': 1, 'returnType': 'json'}),
            ('공공데이터 건축물대장', 'http://apis.data.go.kr/1613000/BldRgstHubService/getBrTitleInfo',
             {'sigunguCd': '11680', 'bjdongCd': '10300', 'bun': '0012', 'ji': '0000', 'numOfRows': 1, 'pageNo': 1, '_type': 'json'}),
        ]
        for name, url, p in tests:
            code, text = ask(url + '?' + urllib.parse.urlencode(dict(p, serviceKey=dg)))
            out.append((name, judge(code, text) if code else '연결 실패(%s)' % text))
    else:
        out.append(('공공데이터', '키 파일 없음'))
    kk = read('kakao_key.txt')
    if kk:
        code, text = ask('https://dapi.kakao.com/v2/local/search/keyword.json?' + urllib.parse.urlencode({'query': '카페', 'size': 1}),
                         {'Authorization': 'KakaoAK ' + kk})
        out.append(('카카오 로컬', judge(code, text) if code else '연결 실패(%s)' % text))
    else:
        out.append(('카카오 로컬', '키 파일 없음'))
    for name, r in out:
        print('키 점검 %s: %s' % (name, r))
    bad = [n for n, r in out if r != '정상']
    print('키 점검 문제 %d개%s' % (len(bad), (': ' + ', '.join(bad)) if bad else ''))


if __name__ == '__main__':
    main()
