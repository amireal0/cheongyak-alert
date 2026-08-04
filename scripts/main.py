from fetch_cheongyak import fetch_all_notices
from filter import filter_notices
from state import load_notified_ids, save_notified_ids, get_notice_id
from notify_kakao import send_message, build_message


def main() -> None:
    all_notices = fetch_all_notices()
    matched = filter_notices(all_notices)

    notified_ids = load_notified_ids()
    new_notices = [n for n in matched if get_notice_id(n) not in notified_ids]

    if not new_notices:
        print("새로운 조건 충족 공고 없음")
        return

    message = build_message(new_notices)
    send_message(message)
    print(f"알림 발송 완료: {len(new_notices)}건")

    notified_ids.update(get_notice_id(n) for n in new_notices)
    save_notified_ids(notified_ids)


if __name__ == "__main__":
    main()
