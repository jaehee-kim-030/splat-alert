# 스플래툰 3 맵·룰 디스코드 알림

카오폴리스 매치(오픈)에서 **만새기 리조트＆스파 + 랭크 바지락** 조합이 나오면 디스코드로 알려줘요.

- 스케줄에 잡히면 바로 알림 (몇 시간 전에 미리)
- 시작 약 15분 전에 한 번 더 알림
- 이미 진행 중이면 "지금 진행 중" 알림

데이터 출처: [Splatoon3.ink](https://splatoon3.ink) (닌텐도 공식 서비스가 아닌 팬 사이트)

## 설치 방법

### 1. 디스코드 웹후크 만들기
1. 알림 받을 디스코드 채널 옆 ⚙️(채널 편집) 클릭
2. **연동** → **웹후크** → **새 웹후크**
3. **웹후크 URL 복사** (이 주소는 비밀번호처럼 다른 사람에게 보여주지 마세요)

### 2. GitHub 저장소 만들기
1. GitHub에서 **New repository** → 이름 예: `splat-alert`
2. **Public**으로 만들기 (공개 저장소는 GitHub Actions 사용이 무료예요)
3. 이 폴더의 파일을 폴더 구조 그대로 올리기
   - `splat_alert.py`
   - `README.md`
   - `.github/workflows/splat-alert.yml`

### 3. 웹후크 주소를 비밀 값으로 등록
1. 저장소 **Settings** → **Secrets and variables** → **Actions**
2. **New repository secret**
3. Name: `DISCORD_WEBHOOK_URL` / Secret: 1번에서 복사한 주소

### 4. 연결 테스트
1. 저장소 **Actions** 탭 → 왼쪽 **스플래툰 맵 알림**
2. **Run workflow** → "디스코드 연결 테스트 메시지만 보내기" 체크 → 실행
3. 디스코드에 ✅ 테스트 메시지가 오면 완료!

그 뒤로는 매시 15분·45분에 자동으로 확인해요.

## 조건 바꾸기
`splat_alert.py` 맨 위 설정 부분의 ID만 바꾸면 돼요.
맵·룰 ID는 https://splatoon3.ink/data/locale/ko-KR.json 에서 찾을 수 있어요.

## 알아두면 좋은 점
- GitHub의 예약 실행은 서버가 붐비면 늦어질 수 있어요. 시작 전 알림을 놓치면 대신 "방금 시작했어요" 알림이 가요.
- 봇이 `state.json`(보낸 알림 기록)을 자동으로 커밋해요. 이 활동 덕분에 공개 저장소의 "60일 동안 활동 없으면 예약 실행 중지" 규칙에도 걸리지 않아요.
