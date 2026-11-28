# 청자다방 본사 매장 목록 받기. run_all.py가 불러 쓴다(csv는 run_all.py가 쓴다).
import os, re, importlib.util
_s = importlib.util.spec_from_file_location('_hq_common', os.path.join(os.path.dirname(os.path.abspath(__file__)), '_common.py'))
C = importlib.util.module_from_spec(_s); _s.loader.exec_module(C)

SOURCE = 'https://www.cheongjadabang.com/bbs/board.php?bo_table=store'


def fetch():
    rows = C.pages(lambda p: SOURCE + '&page=%d' % p,
                   lambda s: re.findall(r'class="store_sbj">(.*?)</div>\s*<div class="store_addr">(.*?)</div>', s, re.S), 100)
    return C.need(rows, 60, '청자다방')
