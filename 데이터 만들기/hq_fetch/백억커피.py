# 백억커피 본사 공식 매장 목록 받기 (run_all.py가 부른다)
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _hq import *

SOURCE = 'https://www.10billioncoffee.co.kr/store'


def fetch():
    h = get('https://www.10billioncoffee.co.kr/store/ajax/list?lat=37.5&lng=127.0')
    return clean(re.findall(r'place-name-distance[^>]*>(.*?)(?:\[|</p>).*?place-address[^>]*>(.*?)</p>', h, re.S))
