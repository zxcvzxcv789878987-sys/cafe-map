# 아리스타커피 본사 공식 매장 목록 받기 (run_all.py가 부른다)
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _hq import *

SOURCE = 'http://www.aristacoffee.co.kr/?module=Shop&action=SiteShop&sMode=SELECT_FORM&iShopNo=1'


def fetch():
    return clean(pages(lambda p: 'http://www.aristacoffee.co.kr/index.php?CurrentPage=%d&module=Shop&action=SiteShop&sMode=SELECT_FORM&iShopNo=1' % p,
                       r'sMode=VIEW_FORM[^>]*>\s*<td>(.*?)</td>\s*<td>(.*?)</td>'))
