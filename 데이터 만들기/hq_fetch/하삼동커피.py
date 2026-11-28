# 하삼동커피 본사 공식 매장 목록 받기 (run_all.py가 부른다)
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _hq import *

SOURCE = 'https://www.hasamdongcoffee.com/store.php'


def fetch():
    form = {'sc_kwd': '', 'sc_sido': '', 'sc_sigugun': '', 'sc_hash_tags': '', 'page': 1, 'sc_ps': 9999}
    h = get('https://www.hasamdongcoffee.com/store_list_ajax.php', form, old_tls=True)
    r = re.findall(r'class="nm"[^>]*>(.*?)</.*?class="addr"[^>]*>(.*?)</', h, re.S)
    return clean((n, a) for n, a in r if re.search(r'\d', txt(a)) and ' ' in txt(a))
