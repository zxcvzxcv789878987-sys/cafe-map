# 인허가 자료 좌표(수정 중부원점 TM, 베셀 타원체, EPSG:5174 계열)를 WGS84 위경도로 바꾼다. 건물 좌표와 견줘 보면 가운데값 2m 차이(2026-11-27).
import math
A_B, F_B = 6377397.155, 1 / 299.1528128
A_W, F_W = 6378137.0, 1 / 298.257223563
TOWGS = (-115.80, 474.99, 674.11, 1.16, -2.31, -1.63, 6.43)
def tm_inv(x, y, lat0=38.0, lon0=127.0028902777778, k0=1.0, fe=200000.0, fn=500000.0, a=A_B, f=F_B):
    e2 = 2 * f - f * f; ep2 = e2 / (1 - e2)
    def M(phi):
        return a * ((1 - e2 / 4 - 3 * e2 ** 2 / 64 - 5 * e2 ** 3 / 256) * phi - (3 * e2 / 8 + 3 * e2 ** 2 / 32 + 45 * e2 ** 3 / 1024) * math.sin(2 * phi)
                    + (15 * e2 ** 2 / 256 + 45 * e2 ** 3 / 1024) * math.sin(4 * phi) - (35 * e2 ** 3 / 3072) * math.sin(6 * phi))
    m = M(math.radians(lat0)) + (y - fn) / k0
    mu = m / (a * (1 - e2 / 4 - 3 * e2 ** 2 / 64 - 5 * e2 ** 3 / 256))
    e1 = (1 - math.sqrt(1 - e2)) / (1 + math.sqrt(1 - e2))
    p1 = mu + (3 * e1 / 2 - 27 * e1 ** 3 / 32) * math.sin(2 * mu) + (21 * e1 ** 2 / 16 - 55 * e1 ** 4 / 32) * math.sin(4 * mu) + (151 * e1 ** 3 / 96) * math.sin(6 * mu) + (1097 * e1 ** 4 / 512) * math.sin(8 * mu)
    n1 = a / math.sqrt(1 - e2 * math.sin(p1) ** 2); t1 = math.tan(p1) ** 2; c1 = ep2 * math.cos(p1) ** 2
    r1 = a * (1 - e2) / (1 - e2 * math.sin(p1) ** 2) ** 1.5; d = (x - fe) / (n1 * k0)
    lat = p1 - (n1 * math.tan(p1) / r1) * (d ** 2 / 2 - (5 + 3 * t1 + 10 * c1 - 4 * c1 ** 2 - 9 * ep2) * d ** 4 / 24 + (61 + 90 * t1 + 298 * c1 + 45 * t1 ** 2 - 252 * ep2 - 3 * c1 ** 2) * d ** 6 / 720)
    lon = math.radians(lon0) + (d - (1 + 2 * t1 + c1) * d ** 3 / 6 + (5 - 2 * c1 + 28 * t1 - 3 * c1 ** 2 + 8 * ep2 + 24 * t1 ** 2) * d ** 5 / 120) / math.cos(p1)
    return lat, lon
def geo2xyz(lat, lon, a, f, h=0.0):
    e2 = 2 * f - f * f; n = a / math.sqrt(1 - e2 * math.sin(lat) ** 2)
    return ((n + h) * math.cos(lat) * math.cos(lon), (n + h) * math.cos(lat) * math.sin(lon), (n * (1 - e2) + h) * math.sin(lat))
def xyz2geo(X, Y, Z, a, f):
    e2 = 2 * f - f * f; p = math.hypot(X, Y); lon = math.atan2(Y, X); lat = math.atan2(Z, p * (1 - e2))
    for _ in range(6):
        n = a / math.sqrt(1 - e2 * math.sin(lat) ** 2); lat = math.atan2(Z + e2 * n * math.sin(lat), p)
    return lat, lon
def to_wgs(x, y, sign=1):
    lat, lon = tm_inv(x, y)
    X, Y, Z = geo2xyz(lat, lon, A_B, F_B)
    dx, dy, dz, rx, ry, rz, s = TOWGS
    rx, ry, rz = (math.radians(v / 3600) * sign for v in (rx, ry, rz)); s = s * 1e-6
    X2 = dx + (1 + s) * (X - rz * Y + ry * Z); Y2 = dy + (1 + s) * (rz * X + Y - rx * Z); Z2 = dz + (1 + s) * (-ry * X + rx * Y + Z)
    la, lo = xyz2geo(X2, Y2, Z2, A_W, F_W)
    return math.degrees(la), math.degrees(lo)
