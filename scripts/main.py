"""공급유형(특별공급/1순위/2순위/무순위/불법행위재공급)별 접수일 전날 저녁 및
당일 아침에 알림을 보낸다. 워크플로우가 하루 두 번(08:30, 20:00 KST) 실행되는
것을 전제로, 현재 시각이 오후(>=14시)면 "내일이 접수 시작일인 것"을 저녁
알림으로, 오전이면 "오늘이 접수 시작일인 것"을 아침 알림으로 보낸다.
한 회차에 여러 건이 해당되더라도 항상 메시지 하나로 모아 보낸다. 저녁
실행(20:00)에서 내일 접수 시작인 공고가 하나도 없으면, 그 사실을 알리는
메시지를 보낸다 (아침 실행에서는 보내지 않음).
"""
import datetime

from fetch_cheongyak import fetch_all_notices, fetch_all_remainder_notices
from filter import collect_candidate_events, passes_area_filter
from state import load_notified_ids, save_notified_ids
from notify_kakao import send_message, build_message

KST_OFFSET = datetime.timedelta(hours=9)


def main() -> None:
    now = datetime.datetime.utcnow() + KST_OFFSET
    today = now.date()
    is_evening_run = now.hour >= 14
    target_offset = 1 if is_evening_run else 0
    kind = "evening_before" if is_evening_run else "morning_of"

    main_notices = fetch_all_notices()
    remainder_notices = fetch_all_remainder_notices()
    candidate_events = collect_candidate_events(main_notices, remainder_notices)

    # 먼저 날짜로 걸러낸다 (API 호출 없는 계산). 전용면적 확인(API 호출)은
    # 오늘/내일 접수인 소수의 후보에 대해서만, 그다음에 한다.
    matching_today = [e for e in candidate_events if (e["start_date"] - today).days == target_offset]
    matching_today = [e for e in matching_today if passes_area_filter(e)]

    if not matching_today:
        if is_evening_run:
            _notify_no_notices(today)
        else:
            print("오늘 접수 시작인 공고 없음")
        return

    notified_ids = load_notified_ids()
    to_send = [
        (f"{e['notice_id']}:{e['type_label']}:{kind}", e)
        for e in matching_today
        if f"{e['notice_id']}:{e['type_label']}:{kind}" not in notified_ids
    ]

    if not to_send:
        print("해당 회차 알림 이미 발송 완료")
        return

    events_to_send = [event for _, event in to_send]
    send_message(build_message(events_to_send))

    for key, _ in to_send:
        notified_ids.add(key)
    save_notified_ids(notified_ids)

    print(f"알림 발송: {len(to_send)}건")
    for _, event in to_send:
        print(f"  - {event['notice'].get('HOUSE_NM')} / {event['type_label']}")


def _notify_no_notices(today: datetime.date) -> None:
    """저녁 실행에서 내일 접수 시작인, 조건에 맞는 공고가 하나도 없을 때 안내."""
    tomorrow = today + datetime.timedelta(days=1)
    empty_key = f"no-notices:{tomorrow.isoformat()}"

    notified_ids = load_notified_ids()
    if empty_key in notified_ids:
        print(f"이미 안내함: 내일({tomorrow.isoformat()}) 해당 공고 없음")
        return

    send_message(f"[청약알림] 내일({tomorrow.isoformat()}) 접수 시작인, 조건에 맞는 서울 공고가 없습니다.")
    notified_ids.add(empty_key)
    save_notified_ids(notified_ids)
    print(f"알림 발송: 내일({tomorrow.isoformat()}) 해당 공고 없음")


if __name__ == "__main__":
    main()
