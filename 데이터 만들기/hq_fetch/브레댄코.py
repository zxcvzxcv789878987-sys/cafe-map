# 브레댄코 본사 공식 매장 목록 받기 (run_all.py가 부른다)
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _hq import *

SOURCE = 'https://www.breadnco.kr/breadnco-store/store/'


def fetch():
    return clean(pages(lambda p: SOURCE + '?pageid=%d&mod=list' % p,
                       r'<td class="kboard-list-branch">(.*?)</td>.*?<a href="[^"]*mod=document[^"]*">(.*?)</a>'))
