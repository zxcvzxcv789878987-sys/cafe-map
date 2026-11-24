# 지도 서버의 문의함(v2/feedback)에 새로 들어온 문의를 읽어서 알려 준다. 지우지 않는다.
# 문의함은 아무도 읽을 수 없게 막혀 있어서, 운영자만 가진 데이터베이스 비밀 키로 읽는다.
# 비밀 키는 이 폴더의 firebase_secret.txt에 한 줄로 넣어 둔다(깃에 올라가지 않는다). 키를 화면에 찍지 않는다.
# 사용법: python -I -X utf8 "데이터 만들기/feedback_report.py"        (지난번 이후 새로 온 것만)
#         python -I -X utf8 "데이터 만들기/feedback_report.py" --all  (전부)
import sys, os, json, urllib.request, urllib.parse, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
DB = 'https://cafe-map-486ae-default-rtdb.firebaseio.com'
KEY_FILE = os.path.join(HERE, 'firebase_secret.txt')
SEEN = os.path.join(HERE, '작업', 'feedback_seen.json')
KIND = {'bug': '앱 오류', 'idea': '기능 제안', 'etc': '기타 문의', 'ask': '기타 문의'}


def main():
    if not os.path.exists(KEY_FILE):
        print('비밀 키 파일이 없다: 데이터 만들기/firebase_secret.txt')
        return 1
    secret = open(KEY_FILE, encoding='utf-8').read().strip()
    try:
        url = DB + '/v2/feedback.json?auth=' + urllib.parse.quote(secret)
        with urllib.request.urlopen(url, timeout=30) as r:
            items = json.load(r) or {}
    except Exception as e:
        # 오류 문구에 주소(비밀 키 포함)가 섞이지 않게 종류만 적는다.
        print('문의함을 받지 못했다:', type(e).__name__)
        return 1
    # 답변(v2/fbreply)도 같이 받아서, 아직 답하지 않은 문의를 알려 준다. 답변은 앱의 메뉴 "받은 문의"에서 적는다.
    try:
        with urllib.request.urlopen(DB + '/v2/fbreply.json?auth=' + urllib.parse.quote(secret), timeout=30) as r:
            replies = json.load(r) or {}
    except Exception as e:
        print('답변을 받지 못했다:', type(e).__name__)
        replies = {}
    todo = [k for k in items if k not in replies]
    print('답변 전 %d건 (앱 메뉴의 받은 문의에서 답할 수 있다)' % len(todo))
    seen = set(json.load(open(SEEN, encoding='utf-8'))) if os.path.exists(SEEN) else set()
    rows = sorted(items.items(), key=lambda kv: (kv[1] or {}).get('t', 0))
    new = rows if '--all' in sys.argv else [kv for kv in rows if kv[0] not in seen]
    print('문의 전체 %d건, 새로 온 것 %d건' % (len(rows), len(new)))
    if not new:
        print('새 문의 없음')
        return 0
    print('새 문의:')
    for k, v in new:
        v = v or {}
        when = datetime.datetime.fromtimestamp(v.get('t', 0) / 1000).strftime('%Y-%m-%d %H:%M') if v.get('t') else ''
        print('---')
        print('[%s] %s%s' % (KIND.get(v.get('k'), v.get('k', '')), when, ' (답변함)' if k in replies else ' (답변 전)'))
        print(v.get('m', ''))
        if v.get('d'):
            print('(기기 정보: %s)' % v['d'])
    if '--all' not in sys.argv:
        os.makedirs(os.path.dirname(SEEN), exist_ok=True)
        json.dump(sorted(seen | {k for k, _ in new}), open(SEEN, 'w', encoding='utf-8'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
