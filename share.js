// 콘센트 좌석 기록을 모두가 같이 보기 위한 서버(Firebase) 주소와 키.
// 둘 다 비어 있으면 기록은 각자의 기기에만 남는다.
// 이 키는 비밀번호가 아니다. 웹 화면에 넣어 쓰라고 만든 공개용 값이고, 누가 무엇을 쓸 수 있는지는 서버의 규칙(firebase-rules.json)이 정한다.
// google: 구글 로그인용 웹 클라이언트 ID(이것도 공개용 값이다). 적혀 있으면 투표할 때 구글 로그인을 받고 한 사람이 한 표만 갖는다.
//         비어 있으면 예전처럼 로그인 없이 투표한다.
window.CAFE_SHARE = {
  key: 'AIzaSyDhIfiAF6logObWpjQq_deLOxdu-VK_mTM',
  db: 'https://cafe-map-486ae-default-rtdb.firebaseio.com',
  google: ''
};
