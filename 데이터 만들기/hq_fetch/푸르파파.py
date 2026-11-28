# 푸르파파 본사 공식 매장 목록 (그룹1). run_all.py가 불러 쓴다.
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _g1 import get, clean, flat, done, imweb_list, imweb_boards, g5_array, SKIP

SOURCE = 'https://www.purpapa.co.kr/STORE'


def fetch():
    parts = get(SOURCE).split('<div class="item-name">')
    rows = []
    for i, p in enumerate(parts[1:]):
        name = p.split("</div>")[0]
        m = re.findall(r'data-addr="([^"]*)"', parts[i])
        cap = re.search(r'class="map_item_caption"[^>]*>(.*?)(?:<div style="position: fixed|</div>\s*</div>\s*</div>)', p, re.S)
        addr = clean(cap.group(1)) if cap else ""
        rows.append((name, addr or (m[-1] if m else "")))
    return done(rows, 10)
