// 폰 홈 화면에 추가해서 앱처럼 쓰기 위한 파일. 한 번 받은 자료를 폰에 넣어 두어서 두 번째부터 빨리 뜨게 한다.
const V = 'cafe-map-v2';   // 자료에 새 칸이 생기면 숫자를 올린다(폰에 넣어 둔 옛 자료를 버린다).
const BIG = /\/(cafes|regions|landmarks)\.js$/;
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', e => e.waitUntil(
  caches.keys().then(ks => Promise.all(ks.filter(k => k !== V).map(k => caches.delete(k)))).then(() => self.clients.claim())
));
self.addEventListener('fetch', e => {
  const u = new URL(e.request.url);
  // 이 지도의 파일만 다룬다. 배경 지도, 카카오, 기록 서버로 가는 요청은 건드리지 않는다.
  if (e.request.method !== 'GET' || u.origin !== location.origin || /cafes\.local\.js$/.test(u.pathname)) return;
  if (BIG.test(u.pathname)) {
    // 큰 자료(카페, 경계, 지하철): 넣어 둔 것이 있으면 그것을 바로 주고, 뒤에서 새것을 받아 다음에 열 때 쓴다.
    e.respondWith(caches.open(V).then(c => c.match(e.request).then(hit => {
      const net = fetch(e.request).then(r => { if (r.ok) c.put(e.request, r.clone()); return r; });
      if (hit) { e.waitUntil(net.catch(() => {})); return hit; }
      return net;
    })));
    return;
  }
  // 나머지(화면, 설정 파일): 인터넷이 되면 새것을 받고, 안 되면 넣어 둔 것을 쓴다.
  e.respondWith(fetch(e.request).then(r => {
    if (r.ok) { const cp = r.clone(); caches.open(V).then(c => c.put(e.request, cp)); }
    return r;
  }).catch(() => caches.match(e.request)));
});
