"""공급유형(특별공급/1순위/2순위/무순위/불법행위재공급)별 접수일 전날 저녁 및
당일 아침에 알림을 보낸다. 워크플로우가 하루 두 번(08:30, 20:00 KST) 실행되는
것을 전제로, 현재 시각이 오후(>=14시)면 "내일이 접수 시작일인 것"을 저녁
알림으로, 오전이면 "오늘이 접수 시작일인 것"을 아침 알림으로 보낸다.
한 번에 여러 건이 해당되면 한 메시지(많이 몰리면 여러 메시지)에 모두 담는다.
"""
import datetime

from fetch_cheongyak import fetch_all_notices, fetch_all_remainder_notices
from filter import collect_events
from state import load_notified_ids, save_notified_ids
from notify_kakao import send_message, build_messages

KST_OFFSET = datetime.timedelta(hours=9)


def main() -> None:
    now = datetime.datetime.utcnow() + KST_OFFSET
    today = now.date()
    is_evening_run = now.hour >= 14

    main_notices = fetch_all_notices()
    remainder_notices = fetch_all_remainder_notices()
    events = collect_events(main_notices, remainder_notices)

    notified_ids = load_notified_ids()
    to_send = []
    for event in events:
        days_left = (event["start_date"] - today).days
        if is_evening_run and days_left == 1:
            kind = "evening_before"
        elif not is_evening_run and days_left == 0:
            kind = "morning_of"
        else:
            continue

        key = f"{event['notice_id']}:{event['type_label']}:{kind}"
        if key in notified_ids:
            continue
        to_send.append((key, event))

    if not to_send:
        print("새로 보낼 알림 없음")
        return

    events_to_send = [event for _, event in to_send]
    for message in build_messages(events_to_send):
        send_message(message)

    for key, _ in to_send:
        notified_ids.add(key)
    save_notified_ids(notified_ids)

    print(f"알림 발송: {len(to_send)}건")
    for _, event in to_send:
        print(f"  - {event['notice'].get('HOUSE_NM')} / {event['type_label']}")


if __name__ == "__main__":
    main()
