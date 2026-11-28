# 커스텀커피 본사 공식 매장 목록 (그룹1). run_all.py가 불러 쓴다.
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _g1 import get, clean, flat, done, imweb_list, imweb_boards, g5_array, SKIP

SOURCE = 'https://kustomcoffee.co.kr/knew/stores.html'


def fetch():
    t = get("https://kustomcoffee.co.kr/knew/stores-data.js")
    s = json.loads(t[t.find("{"):t.rfind("}") + 1])["stores"]
    return done([(x["name"], x["addr"]) for x in s
                 if not re.search(r"오픈|예정|준비|폐점", (x.get("kind") or "") + x["name"])], 60)
