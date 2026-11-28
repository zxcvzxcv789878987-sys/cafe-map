# 아몽즈커피 본사 공식 매장 목록 (그룹1). run_all.py가 불러 쓴다.
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _g1 import get, clean, flat, done, imweb_list, imweb_boards, g5_array, SKIP

SOURCE = 'https://www.amongzcoffee.co.kr/store'


def fetch():
    t = get(SOURCE)
    rows = []
    for m in re.finditer(r'<div id="caption_(\d+)" style="display:none">\s*<h4>(.*?)</h4>\s*<p>(.*?)</p>', t, re.S):
        parts = [clean(p) for p in re.split(r"<br\s*/?>", m.group(3))]
        addr = next((p for p in parts if re.match(r"(서울|부산|대구|인천|광주|대전|울산|세종|경기|강원|충청|충북|충남|전라|전북|전남|경상|경북|경남|제주)", p)), "")
        rows.append((m.group(2), addr))
    return done(rows, 8)
