// 콘센트 좌석 기록을 모두가 같이 보기 위한 서버(Firebase) 주소와 키.
// 둘 다 비어 있으면 기록은 각자의 기기에만 남는다.
// 이 키는 비밀번호가 아니다. 웹 화면에 넣어 쓰라고 만든 공개용 값이고, 누가 무엇을 쓸 수 있는지는 서버의 규칙(firebase-rules.json)이 정한다.
// google: 구글 로그인용 웹 클라이언트 ID(이것도 공개용 값이다). 적혀 있으면 투표할 때 구글 로그인을 받고 한 사람이 한 표만 갖는다.
//         비어 있으면 예전처럼 로그인 없이 투표한다.
window.CAFE_SHARE = {
  key: 'AIzaSyDhIfiAF6logObWpjQq_deLOxdu-VK_mTM',
  db: 'https://cafe-map-486ae-default-rtdb.firebaseio.com',
  google: '591551793146-5f7t31sr9iom3p8vmhg3b9gac3kicu43.apps.googleusercontent.com',
  // admin: 운영자 계정 번호(공개해도 되는 값). 운영자의 투표는 투표 수에는 들어가지만, 다른 사람의 "첫 콘센트 투표" 2배를 빼앗지 않고, 운영자는 2배를 받지 않는다.
  admin: 'YJZkK7gP9xYP2fBjh2KWnJHDOsl1',
  // 운영자 계정의 무작위 번호(기록과 폐업 신고 칸 이름). 운영자 기록을 "운영자"로 보여 줄 때 쓴다(2026-11-27).
  adminA: 'kria1f6tx427'
};
