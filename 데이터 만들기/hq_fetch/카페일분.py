# 카페일분 본사 매장 목록 받기. run_all.py가 불러 쓴다(csv는 run_all.py가 쓴다).
import os, re, importlib.util
_s = importlib.util.spec_from_file_location('_hq_common', os.path.join(os.path.dirname(os.path.abspath(__file__)), '_common.py'))
C = importlib.util.module_from_spec(_s); _s.loader.exec_module(C)

SOURCE = 'https://www.cafeilboon.com/%EB%A7%A4%EC%9E%A5%EC%B0%BE%EA%B8%B0'


def fetch():
    # 이 페이지는 404 상태로 오지만 내용은 정상이라 본문을 그대로 읽는다.
    s = C.get(SOURCE, body_on_error=True)
    return C.need(re.findall(r'class="item-name">(.*?)</div>\s*<div class="map_item_caption"[^>]*>(.*?)</div>\s*</div>', s, re.S), 50, '카페일분')
