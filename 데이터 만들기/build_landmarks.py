# 지하철 노선(호선 색), 지하철역, 아파트 단지를 지도에 올릴 수 있게 landmarks.js로 만든다.
# 자료는 모두 OpenStreetMap(Overpass API)에서 받은 것이다. 출처 표시: © OpenStreetMap 기여자 (ODbL)
# 사용법: python -X utf8 build_landmarks.py <노선 geom.json> <역 stations.json> <아파트 apt.json> <출력 landmarks.js>
import sys, json, math, collections, os, re
from shapely.geometry import LineString, MultiLineString, Point
from shapely.ops import linemerge
from shapely.strtree import STRtree

geom_path, st_path, apt_path, out_path = sys.argv[1:5]
KX, KY = 111320 * math.cos(math.radians(36.5)), 110540   # 경위도를 미터로 어림하는 배율


def color(c):
    c = (c or '').strip()
    if c.lower() == 'yellow':
        return '#F5B800'
    return c.upper() if re.match(r'^#[0-9a-fA-F]{6}$', c) else None


def enc(coords):
    """좌표를 정수 차이값으로 줄인다."""
    flat, px, py = [], 0, 0
    for x, y in coords:
        x, y = round(x * 1e5), round(y * 1e5)
        flat += [x - px, y - py]
        px, py = x, y
    return flat


# ---------- 1. 노선 ----------
els = json.load(open(geom_path, encoding='utf-8'))['elements']
ways = {e['id']: e for e in els if e['type'] == 'way' and 'geometry' in e}
way_color, order = {}, {'subway': 0, 'light_rail': 1, 'monorail': 1, 'train': 2}
rels = sorted((e for e in els if e['type'] == 'relation'), key=lambda e: order.get(e['tags'].get('route'), 3))
line_name = {}
for r in rels:
    c = color(r['tags'].get('colour'))
    if not c:
        continue
    line_name.setdefault(c, r['tags'].get('ref') or r['tags'].get('name', ''))
    for m in r['members']:
        if m['type'] != 'way' or m['ref'] not in ways or m.get('role', '') in ('platform', 'stop'):
            continue
        t = ways[m['ref']].get('tags', {})
        # 차량기지로 들어가는 선로와 승강장은 뺀다.
        if t.get('railway') not in ('subway', 'rail', 'light_rail', 'monorail', 'narrow_gauge') or 'service' in t:
            continue
        way_color.setdefault(m['ref'], c)

by_color = collections.defaultdict(list)
metric_lines, metric_color = [], []
for wid, c in way_color.items():
    pts = [(p['lon'], p['lat']) for p in ways[wid]['geometry']]
    if len(pts) < 2:
        continue
    by_color[c].append(LineString(pts))
    metric_lines.append(LineString([(x * KX, y * KY) for x, y in pts]))
    metric_color.append(c)

lines = []
for c, parts in by_color.items():
    merged = linemerge(MultiLineString(parts)).simplify(0.00006)
    segs = list(merged.geoms) if merged.geom_type == 'MultiLineString' else [merged]
    lines.append({'c': c, 'n': line_name.get(c, ''), 'g': [enc(s.coords) for s in segs if len(s.coords) >= 2]})
print('노선 색', len(lines), '선로 조각', sum(len(l['g']) for l in lines))

# ---------- 2. 역: 노선에서 60m 안에 있는 역만 남기고, 지나는 노선 색을 붙인다 ----------
tree = STRtree(metric_lines)
raw = []
for e in json.load(open(st_path, encoding='utf-8'))['elements']:
    t = e.get('tags', {})
    name = t.get('name:ko') or t.get('name')
    if not name:
        continue
    pt = Point(e['lon'] * KX, e['lat'] * KY)
    cols = []
    for i in tree.query(pt.buffer(60)):
        if metric_lines[i].distance(pt) <= 60 and metric_color[i] not in cols:
            cols.append(metric_color[i])
    if cols:
        name = re.sub(r'\s*\(.*?\)\s*', '', name).strip()
        raw.append([e['lon'], e['lat'], name if name.endswith('역') else name + '역', cols])

# 환승역은 노선마다 점이 따로 있다. 이름이 같고 400m 안에 있으면 하나로 합친다.
stations = []
for lon, lat, name, cols in raw:
    for s in stations:
        if s[2] == name and math.hypot((s[0] / s[4] - lon) * KX, (s[1] / s[4] - lat) * KY) < 400:
            s[0] += lon; s[1] += lat; s[4] += 1
            s[3] += [c for c in cols if c not in s[3]]
            break
    else:
        stations.append([lon, lat, name, list(cols), 1])
stations = [[round(s[0] / s[4] * 1e5), round(s[1] / s[4] * 1e5), s[2], s[3]] for s in stations]
print('역', len(stations), '환승역', sum(1 for s in stations if len(s[3]) > 1))

# ---------- 3. 아파트 단지 ----------
APT = re.compile(r'아파트|단지|자이|래미안|푸르지오|힐스테이트|아이파크|롯데캐슬|e편한세상|더샵|SK뷰|맨션|타운|빌리지|캐슬|파크')
apts, seen = [], set()
for e in json.load(open(apt_path, encoding='utf-8'))['elements']:
    t = e.get('tags', {})
    name = (t.get('name:ko') or t.get('name') or '').strip()
    c = e.get('center') or ({'lon': e['lon'], 'lat': e['lat']} if 'lon' in e else None)
    if not name or not c or not (t.get('residential') == 'apartments' or APT.search(name)):
        continue
    key = (name, round(c['lon'], 3), round(c['lat'], 3))
    if key in seen:
        continue
    seen.add(key)
    apts.append([round(c['lon'] * 1e5), round(c['lat'] * 1e5), name])
print('아파트 단지', len(apts))

with open(out_path, 'w', encoding='utf-8') as o:
    o.write('window.LANDMARKS=')
    json.dump({'lines': lines, 'stations': stations, 'apts': apts}, o, ensure_ascii=False, separators=(',', ':'))
    o.write(';')
print('파일', os.path.getsize(out_path))
