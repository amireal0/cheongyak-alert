# 청약 알림봇 (서울 · 전용 30~80㎡ · 아파트 분양)

청약홈(한국부동산원) Open API에서 신규 아파트 분양 공고를 가져와,
서울 지역 / 전용면적 30㎡~80㎡ 조건에 맞는 공고를, 공급유형별(특별공급/
1순위/2순위/무순위/불법행위재공급) **접수일 전날 저녁 및 당일 아침**에
카카오톡 "나에게 보내기"로 알림을 보내는 도구입니다.

청약홈 Open API는 LH·SH가 공급하는 공공분양 아파트를 포함한
전국 APT 분양 공고를 통합 제공하므로, 이 API 하나로 청약홈/LH/SH
아파트 분양 공고를 대부분 커버할 수 있습니다. (LH·SH 임대주택 등
아파트 "분양"이 아닌 유형은 범위에서 제외했습니다.)

## 사전 준비 (본인이 직접 해야 하는 것)

### 1. 공공데이터포털 API 키 발급
1. https://www.data.go.kr 회원가입
2. "한국부동산원_청약홈_APT 분양정보" 검색 → 활용신청 (승인은 보통 즉시~1일)
3. 마이페이지에서 서비스키(디코딩 키) 확인

### 2. 카카오 "나에게 보내기" 설정
1. https://developers.kakao.com 에서 애플리케이션 생성
2. 제품설정 > 카카오 로그인 활성화 ON
3. 제품설정 > 카카오 로그인 > Redirect URI에 임의 주소 등록
   (예: `http://localhost:5000`, 실제로 그 주소가 떠 있을 필요는 없음)
4. 제품설정 > 카카오 로그인 > 동의항목에서 "카카오톡 메시지 전송"
   (talk_message) 활성화
5. 앱설정 > 앱 > 고급 > "클라이언트 시크릿"에서 "카카오 로그인" 코드의
   활성화 상태를 확인. **ON이면 반드시 그 코드 값을 `KAKAO_CLIENT_SECRET`으로
   준비**해야 한다 (OFF로 표시돼도 실제로는 필수로 요구되는 경우가 있었으니,
   토큰 교환이 `invalid_client`로 실패하면 이 값을 넣어서 다시 시도할 것).
6. 아래 명령으로 최초 1회 authorization code → access_token,
   refresh_token 발급:
   ```bash
   pip install -r requirements.txt
   python scripts/get_kakao_token.py
   ```
   안내에 따라 브라우저에서 로그인 URL을 열어 로그인/동의한 뒤,
   리다이렉트된 주소의 `code=` 값을 터미널에 붙여넣으면
   `KAKAO_REFRESH_TOKEN` 값을 출력해준다. Client Secret이 필요한
   앱이면 실행 중 물어볼 때 같이 입력한다.
7. 발급받은 값들을 GitHub 저장소의 Settings > Secrets and variables >
   Actions 에 등록:
   - `KAKAO_REST_API_KEY`
   - `KAKAO_REFRESH_TOKEN`
   - `KAKAO_CLIENT_SECRET` (Client Secret을 쓰는 경우에만)
   - `DATA_GO_KR_API_KEY`

카카오 access_token은 6시간, refresh_token은 2개월(갱신 시 연장)마다
만료됩니다. `scripts/notify_kakao.py`는 실행 시마다 refresh_token으로
access_token을 새로 발급받으므로, refresh_token만 주기적으로
(2개월 내) 갱신해주면 됩니다.

## 구조

```
scripts/
  fetch_cheongyak.py    # 청약홈 Open API 호출 → 신규 공고 원본 리스트
  filter.py              # 지역/전용면적 조건으로 필터링
  state.py                # 이미 알림 보낸 공고 ID 관리 (state.json)
  notify_kakao.py          # 카카오 "나에게 보내기" 발송
  get_kakao_token.py        # 카카오 최초 access_token/refresh_token 발급 (1회 실행)
  main.py                    # 위 단계를 순서대로 실행
state.json                # 알림 이력 (GitHub Actions가 커밋으로 관리)
.github/workflows/
  cheongyak-check.yml    # 매일 아침 8시 / 저녁 8시(KST) 실행
```

## 필터 조건 (scripts/filter.py에서 수정 가능)

- 공급지역명: 서울
- 전용면적: 30㎡ 이상 80㎡ 이하 (특별공급/1순위/2순위 공고에만 적용됨 —
  무순위/불법행위재공급은 API에 전용면적 정보가 없어 지역 조건만 적용)
- 주택구분: 아파트 (분양) — 임대 제외 (무순위/불법행위재공급은 성격상 제외 안 함)

## 알림 시점과 형식

`main.py`가 하루 두 번(08:30, 20:00 KST) 실행되는 것을 전제로, 공급유형별
접수 시작일을 기준으로 **접수일 전날 저녁(20:00 실행분) / 당일 아침(08:30
실행분)** 딱 한 번씩만 알림을 보냅니다. 워크플로우를 다른 시각에 수동
실행하면 14시를 기준으로 오전/오후를 판단합니다.

알림 메시지에는 공급유형 구분, 공고명(지역), 청약접수일, 접수 사이트
(청약홈 링크)가 담깁니다:

```
[청약알림] 특별공급
월계 중흥S-클래스 리비에르 (서울)
접수: 2026-07-27 ~ 2026-07-30
https://www.applyhome.co.kr/...
```

지원하는 공급유형: 특별공급, 1순위, 2순위, 무순위, 불법행위재공급.
**임의공급은 청약홈 Open API에 별도로 공개되어 있지 않아 미지원**입니다
(실제로 25개 이상의 오퍼레이션 이름과 전체 데이터셋을 확인했으나 찾지
못함).

## 로컬 테스트

```bash
pip install -r requirements.txt
export DATA_GO_KR_API_KEY=...
export KAKAO_REST_API_KEY=...
export KAKAO_REFRESH_TOKEN=...
export KAKAO_CLIENT_SECRET=...  # Client Secret을 쓰는 경우에만
python scripts/main.py
```

## 청약홈 Open API 참고사항

`scripts/fetch_cheongyak.py`는 실제 서비스키로 호출해 확인한 필드명을
기준으로 작성되었습니다 (odcloud 플랫폼, `serviceKey` 파라미터 사용).

- `getAPTLttotPblancDetail`: 공고 목록/상세. `HOUSE_NM`(주택명),
  `SUBSCRPT_AREA_CODE_NM`(공급지역명), `HOUSE_SECD_NM`(주택구분명, "APT" 등),
  `RENT_SECD_NM`(분양구분명, "분양주택"/"임대주택"), `RCRIT_PBLANC_DE`(모집공고일),
  `HOUSE_MANAGE_NO`/`PBLANC_NO`(공고 식별자) 등을 제공하지만 **전용면적은
  포함하지 않습니다.**
- `getAPTLttotPblancMdl`: 공고별 주택형 상세. `HOUSE_TY` 필드에 전용면적이
  들어있습니다 (예: `"084.9165A"` → 84.9165㎡, 끝에 모델 구분 알파벳이
  붙기도 함). `filter.py`가 공고마다 이 API를 추가 호출해 전용면적을 확인합니다.
- `getRemndrLttotPblancDetail`: 무순위/불법행위재공급 공고. 같은 API가
  `HOUSE_SECD_NM` 값("무순위" / "불법행위 재공급")으로 두 유형을 함께
  제공합니다. 접수기간은 `SUBSCRPT_RCEPT_BGNDE`/`SUBSCRPT_RCEPT_ENDDE`.
  전용면적 필드가 아예 없고, 이 공고들의 `HOUSE_MANAGE_NO`로
  `getAPTLttotPblancMdl`을 조회해도 데이터가 없습니다.
- 세 API 모두 `cond[FIELD::OP]=value` 형태의 조건 검색을 지원합니다
  (예: `cond[RCRIT_PBLANC_DE::GTE]=2026-07-01`). `fetch_notices`/
  `fetch_remainder_notices`는 이를 이용해 최근 공고만 가져옵니다 (기본 45일).
