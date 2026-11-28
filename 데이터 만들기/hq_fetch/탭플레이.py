# 탭플레이 본사 매장 목록 받기. run_all.py가 불러 쓴다(csv는 run_all.py가 쓴다).
import os, re, importlib.util
_s = importlib.util.spec_from_file_location('_hq_common', os.path.join(os.path.dirname(os.path.abspath(__file__)), '_common.py'))
C = importlib.util.module_from_spec(_s); _s.loader.exec_module(C)

SOURCE = 'https://www.taplay.co.kr/myboard/st_branch'


def fetch():
    u = ('https://www.taplay.co.kr/shop_contents/myboard_list.htm?load_type=&page_idx=0&myboard_code=st_branch&me_popup='
         '&h_search_c=0&h_search_v=&tag_on=&page_limit=10&page=%d&category_idx=&extent_str=')
    rows = C.pages(lambda p: u % p, lambda s: re.findall(r'class="res-m-show title">(.*?)<div>.*?</span>\s*<span class="res-m-show">(.*?)</span>', s, re.S), 20)
    return C.need(rows, 6, '탭플레이')
