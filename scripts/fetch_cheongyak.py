"""
청약홈(한국부동산원) APT 분양정보 Open API 호출.

공공데이터포털 서비스: "한국부동산원_청약홈 분양정보 조회 서비스"
https://www.data.go.kr/data/15098547/openapi.do

2026-08-04에 실제 서비스키로 호출해 확인한 필드명 기준으로 작성됨:

- getAPTLttotPblancDetail (공고 목록/상세)
  주요 필드: HOUSE_MANAGE_NO, PBLANC_NO, HOUSE_NM, HOUSE_SECD_NM("APT" 등),
  RENT_SECD_NM("분양주택"/"임대주택"), SUBSCRPT_AREA_CODE_NM(공급지역명, 예 "서울"),
  RCRIT_PBLANC_DE(모집공고일, YYYY-MM-DD) 등. 이 API 응답에는 전용면적이 없음.

- getAPTLttotPblancMdl (공고별 주택형/전용면적 상세)
  주요 필드: HOUSE_MANAGE_NO, PBLANC_NO, HOUSE_TY(전용면적, 예 "084.9165A" ->
  84.9165㎡, 뒤에 모델 구분 알파벳이 붙기도 함), SUPLY_AR(공급면적) 등.

두 API 모두 odcloud 플랫폼(uddi 3.0) 응답 포맷을 사용:
  {"data": [...], "page":.., "perPage":.., "matchCount":.., "totalCount":..}
날짜 범위 등 조건 검색은 `cond[FIELD::OP]=value` 형태의 쿼리 파라미터로 지정한다
(OP: EQ, GTE, LTE 등). 서비스키는 발급받은 형태(인코딩/디코딩) 그대로
serviceKey 파라미터에 넣으면 된다.
"""
import os
import re
from datetime import date, timedelta

import requests

BASE_URL = "https://api.odcloud.kr/api/ApplyhomeInfoDetailSvc/v1"


def _request(operation: str, params: dict) -> dict:
    api_key = os.environ["DATA_GO_KR_API_KEY"]
    resp = requests.get(
        f"{BASE_URL}/{operation}",
        params={**params, "serviceKey": api_key},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def fetch_notices(page_no: int = 1, num_of_rows: int = 100, recent_days: int = 45) -> list[dict]:
    """최근 recent_days일 이내에 모집공고가 난 APT 분양 공고 한 페이지를 가져온다."""
    since = (date.today() - timedelta(days=recent_days)).isoformat()
    data = _request(
        "getAPTLttotPblancDetail",
        {
            "page": page_no,
            "perPage": num_of_rows,
            "cond[RCRIT_PBLANC_DE::GTE]": since,
        },
    )
    return data.get("data", [])


def fetch_all_notices(num_of_rows: int = 100, recent_days: int = 45, max_pages: int = 10) -> list[dict]:
    """조건에 맞는 공고를 페이지를 순회하며 모두 가져온다."""
    notices: list[dict] = []
    for page_no in range(1, max_pages + 1):
        page_items = fetch_notices(page_no=page_no, num_of_rows=num_of_rows, recent_days=recent_days)
        if not page_items:
            break
        notices.extend(page_items)
        if len(page_items) < num_of_rows:
            break
    return notices


def fetch_unit_areas(house_manage_no: str, pblanc_no: str) -> list[float]:
    """공고의 주택형(HOUSE_TY)별 전용면적(㎡) 목록을 가져온다."""
    data = _request(
        "getAPTLttotPblancMdl",
        {
            "page": 1,
            "perPage": 100,
            "cond[HOUSE_MANAGE_NO::EQ]": house_manage_no,
            "cond[PBLANC_NO::EQ]": pblanc_no,
        },
    )
    areas = []
    for row in data.get("data", []):
        house_ty = row.get("HOUSE_TY")
        if not house_ty:
            continue
        # 예: "084.9165A" -> 84.9165 (뒤에 모델 구분 알파벳이 붙기도 함)
        match = re.match(r"\s*([\d.]+)", str(house_ty))
        if match:
            areas.append(float(match.group(1)))
    return areas


if __name__ == "__main__":
    notices = fetch_all_notices(max_pages=1)
    print(f"공고 {len(notices)}건 수신")
    for n in notices[:3]:
        print(n.get("HOUSE_NM"), n.get("SUBSCRPT_AREA_CODE_NM"), n.get("RENT_SECD_NM"))
