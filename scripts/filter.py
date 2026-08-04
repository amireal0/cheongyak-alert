"""서울 지역 / 전용면적 30㎡~80㎡ / 아파트 분양 조건으로 공고를 필터링.

실제 청약홈 Open API(getAPTLttotPblancDetail / getAPTLttotPblancMdl) 응답을
직접 호출해 확인한 필드명 기준으로 작성됨. 전용면적은 목록 API에 없어
공고별로 fetch_unit_areas를 호출해 주택형별 상세에서 가져온다.
"""
from fetch_cheongyak import fetch_unit_areas

MIN_AREA = 30  # ㎡ (전용면적 이상)
MAX_AREA = 80  # ㎡ (전용면적 이하)

REGION_KEYWORD = "서울"


def _is_region_match(notice: dict) -> bool:
    return REGION_KEYWORD in (notice.get("SUBSCRPT_AREA_CODE_NM") or "")


def _is_apartment_sale(notice: dict) -> bool:
    """임대가 아닌 아파트 분양 공고인지 판단."""
    house_secd_nm = notice.get("HOUSE_SECD_NM") or ""
    rent_secd_nm = notice.get("RENT_SECD_NM") or ""
    return "APT" in house_secd_nm and "임대" not in rent_secd_nm


def _has_area_in_range(notice: dict) -> bool:
    house_manage_no = notice.get("HOUSE_MANAGE_NO")
    pblanc_no = notice.get("PBLANC_NO")
    if not house_manage_no or not pblanc_no:
        return True
    areas = fetch_unit_areas(house_manage_no, pblanc_no)
    if not areas:
        # 주택형 정보를 못 가져오면 일단 통과시키고 알림 문구에서 확인 유도
        return True
    return any(MIN_AREA <= area <= MAX_AREA for area in areas)


def matches(notice: dict) -> bool:
    if not _is_region_match(notice):
        return False
    if not _is_apartment_sale(notice):
        return False
    return _has_area_in_range(notice)


def filter_notices(notices: list[dict]) -> list[dict]:
    return [n for n in notices if matches(n)]
