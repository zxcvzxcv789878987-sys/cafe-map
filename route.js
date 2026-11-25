// 걷는 길 찾기에 쓰는 키. 웹 화면에 넣어 쓰는 공개용 값이다.
// geoapify(Geoapify, 무료 하루 3,000번), ors(OpenRouteService) 순으로 쓰고, 둘 다 비었거나 실패하면
// FOSSGIS가 무료로 여는 오픈스트리트맵 걷기 경로 서버(routing.openstreetmap.de)를 쓴다(적게 쓰는 조건).
window.CAFE_ROUTE = {
  geoapify: '9872ce7c3fc847d7bc91fdb7ec2495d7',
  ors: ''
};
