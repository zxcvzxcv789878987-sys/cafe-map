# 이공커피 본사 매장 목록 받기. run_all.py가 불러 쓴다(csv는 run_all.py가 쓴다).
import os, re, importlib.util
_s = importlib.util.spec_from_file_location('_hq_common', os.path.join(os.path.dirname(os.path.abspath(__file__)), '_common.py'))
C = importlib.util.module_from_spec(_s); _s.loader.exec_module(C)

SOURCE = 'https://www.yigongcoffee.com/'


def fetch():
    # 매장 목록이 사이트 스크립트 안에 들어 있다.
    s = C.get(SOURCE)
    js = re.search(r'src="(/assets/index-[^"]+\.js)"', s).group(1)
    t = C.get('https://www.yigongcoffee.com' + js)
    i = t.find('title:"흑석본점"')
    seg = t[i - 50:t.find('}]', i) + 2]
    return C.need(re.findall(r'title:"(.*?)",address:"(.*?)"', seg), 10, '이공커피')
