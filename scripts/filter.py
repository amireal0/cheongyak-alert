"""서울 지역 / 전용면적 30㎡~80㎡ / 아파트 분양 공고에서, 공급유형(특별공급/
1순위/2순위/무순위/불법행위재공급)별 접수기간을 뽑아 알림 이벤트로 변환한다.

실제 청약홈 Open API(getAPTLttotPblancDetail / getAPTLttotPblancMdl /
getRemndrLttotPblancDetail) 응답을 직접 호출해 확인한 필드명 기준으로 작성됨.
무순위/불법행위재공급 공고는 전용면적 정보 자체가 API에 없어 지역 조건만 적용한다
(자세한 내용은 fetch_cheongyak.py 참고).

전용면적 확인(fetch_unit_areas)은 공고마다 API를 한 번 더 호출하는 비용이
드는 작업이라, collect_candidate_events()에서는 지역/주택구분만으로 이벤트를
추리고, 실제로 오늘/내일 접수인지(날짜 확인, API 호출 없음)까지 걸러낸 뒤에야
passes_area_filter()로 전용면적을 확인하도록 main.py에서 순서를 조정한다.
"""
from datetime import date

from fetch_cheongyak import fetch_unit_areas

MIN_AREA = 30  # ㎡ (전용면적 이상)
MAX_AREA = 80  # ㎡ (전용면적 이하)

REGION_KEYWORD = "서울"

# (표시명, 접수시작일 후보 필드들, 접수종료일 후보 필드들). 후보가 여럿인 건
# 1순위/2순위가 해당지역/기타경기/기타지역으로 접수일이 나뉘어 있어서이고,
# 그 중 가장 이른 시작일 ~ 가장 늦은 종료일을 그 구분의 접수기간으로 본다.
_MAIN_EVENT_GROUPS = [
    ("특별공급", ["SPSPLY_RCEPT_BGNDE"], ["SPSPLY_RCEPT_ENDDE"]),
    (
        "1순위",
        ["GNRL_RNK1_CRSPAREA_RCPTDE", "GNRL_RNK1_ETC_GG_RCPTDE", "GNRL_RNK1_ETC_AREA_RCPTDE"],
        ["GNRL_RNK1_CRSPAREA_ENDDE", "GNRL_RNK1_ETC_GG_ENDDE", "GNRL_RNK1_ETC_AREA_ENDDE"],
    ),
    (
        "2순위",
        ["GNRL_RNK2_CRSPAREA_RCPTDE", "GNRL_RNK2_ETC_GG_RCPTDE", "GNRL_RNK2_ETC_AREA_RCPTDE"],
        ["GNRL_RNK2_CRSPAREA_ENDDE", "GNRL_RNK2_ETC_GG_ENDDE", "GNRL_RNK2_ETC_AREA_ENDDE"],
    ),
]


def _parse_date(value) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        return None


def _date_range(notice: dict, begin_keys: list[str], end_keys: list[str]) -> tuple[date, date] | None:
    begins = [d for d in (_parse_date(notice.get(k)) for k in begin_keys) if d]
    ends = [d for d in (_parse_date(notice.get(k)) for k in end_keys) if d]
    if not begins or not ends:
        return None
    return min(begins), max(ends)


def _is_region_match(notice: dict) -> bool:
    return REGION_KEYWORD in (notice.get("SUBSCRPT_AREA_CODE_NM") or "")


def _is_apartment_sale(notice: dict) -> bool:
    """임대가 아닌 아파트 분양 공고인지 판단."""
    house_secd_nm = notice.get("HOUSE_SECD_NM") or ""
    rent_secd_nm = notice.get("RENT_SECD_NM") or ""
    return "APT" in house_secd_nm and "임대" not in rent_secd_nm


_area_cache: dict[str, list[float]] = {}


def _has_area_in_range(notice: dict) -> bool:
    house_manage_no = notice.get("HOUSE_MANAGE_NO")
    pblanc_no = notice.get("PBLANC_NO")
    if not house_manage_no or not pblanc_no:
        return True
    cache_key = f"{house_manage_no}:{pblanc_no}"
    if cache_key not in _area_cache:
        _area_cache[cache_key] = fetch_unit_areas(house_manage_no, pblanc_no)
    areas = _area_cache[cache_key]
    if not areas:
        # 주택형 정보를 못 가져오면 일단 통과시키고 알림 문구에서 확인 유도
        return True
    return any(MIN_AREA <= area <= MAX_AREA for area in areas)


def passes_area_filter(event: dict) -> bool:
    """이벤트가 전용면적 조건을 만족하는지 확인한다 (main 공고만 API 호출 발생,
    무순위/불법행위재공급은 애초에 면적 정보가 없어 항상 통과)."""
    if event["source"] != "main":
        return True
    return _has_area_in_range(event["notice"])


def _make_event(notice: dict, type_label: str, start: date, end: date, source: str) -> dict:
    return {
        "notice": notice,
        "notice_id": notice.get("PBLANC_NO") or notice.get("HOUSE_MANAGE_NO"),
        "type_label": type_label,
        "start_date": start,
        "end_date": end,
        "source": source,
    }


def extract_main_events(notice: dict) -> list[dict]:
    """특별공급/1순위/2순위 접수기간을 이벤트로 뽑는다."""
    events = []
    for label, begin_keys, end_keys in _MAIN_EVENT_GROUPS:
        date_range = _date_range(notice, begin_keys, end_keys)
        if date_range is None:
            continue
        start, end = date_range
        events.append(_make_event(notice, label, start, end, source="main"))
    return events


def extract_remainder_events(notice: dict) -> list[dict]:
    """무순위/불법행위재공급 접수기간을 이벤트로 뽑는다."""
    start = _parse_date(notice.get("SUBSCRPT_RCEPT_BGNDE"))
    end = _parse_date(notice.get("SUBSCRPT_RCEPT_ENDDE"))
    if not start or not end:
        return []
    type_label = notice.get("HOUSE_SECD_NM") or "무순위"
    return [_make_event(notice, type_label, start, end, source="remainder")]


def collect_candidate_events(main_notices: list[dict], remainder_notices: list[dict]) -> list[dict]:
    """서울 + 주택구분 조건에 맞는 공고들의 접수 이벤트를 모은다.

    전용면적은 아직 확인하지 않는다 (API 호출 비용이 있어서, 날짜까지
    걸러낸 뒤 passes_area_filter()로 나중에 확인하는 게 더 효율적이다).
    """
    events: list[dict] = []

    for notice in main_notices:
        if not _is_region_match(notice):
            continue
        if not _is_apartment_sale(notice):
            continue
        events.extend(extract_main_events(notice))

    for notice in remainder_notices:
        if not _is_region_match(notice):
            continue
        events.extend(extract_remainder_events(notice))

    return events
