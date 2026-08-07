"""공급유형(특별공급/1순위/2순위/무순위/불법행위재공급)별 접수일 전날 저녁 및
당일 아침에 알림을 보낸다. 하루 두 번(08:37, 20:13 KST 근처) 실행되는 것을
전제로, 저녁 실행이면 "내일이 접수 시작일인 것"을, 아침 실행이면 "오늘이
접수 시작일인 것"을 알린다. 해당하는 공고가 하나도 없어도, 아침/저녁 모두
"없다"는 메시지를 보낸다.

아침/저녁 판단은 다음 순서로 한다:
1. GITHUB_EVENT_INPUTS_KIND ("morning"/"evening") — workflow_dispatch를 외부
   (예: cron-job.org)에서 호출할 때 명시적으로 넘기는 값. 어떤 트리거가 이
   실행을 걸었는지 실행 시각과 무관하게 정확히 알 수 있어 가장 신뢰도가 높다.
2. GITHUB_EVENT_SCHEDULE (트리거한 cron 문자열) — GitHub Actions 자체
   schedule 트리거로 실행된 경우에만 채워짐.
3. 위 둘 다 없으면(예: GitHub UI에서 입력 없이 수동 실행) 현재 시각(14시
   기준)으로 추정.

GitHub Actions의 schedule 트리거는 부하가 몰리면 몇 시간씩 지연될 수 있어서
(실제로 저녁 실행이 다음날 새벽으로 지연된 적이 있음), 실행된 시각(시계)만으로
아침/저녁을 판단하면 지연된 저녁 실행이 아침으로 잘못 분류되는 문제가 있었다.
1·2번 값이 있으면 시계와 무관하게 정확히 판단하므로 이 문제가 없다. 자정을
넘겨서까지 지연된 저녁 실행이면 "오늘 날짜"도 하루 전(원래 저녁이었던 날)으로
보정한다.

한 회차에 여러 건이 해당되더라도 항상 메시지 하나로 모아 보낸다.
"""
import datetime
import os

from fetch_cheongyak import fetch_all_notices, fetch_all_remainder_notices
from filter import collect_candidate_events, passes_area_filter
from state import load_notified_ids, save_notified_ids
from notify_kakao import send_message, build_message

KST_OFFSET = datetime.timedelta(hours=9)
MORNING_CRON = "37 23 * * *"
EVENING_CRON = "13 11 * * *"


def _is_evening_run(now: datetime.datetime) -> bool:
    kind_input = os.environ.get("GITHUB_EVENT_INPUTS_KIND")
    if kind_input == "evening":
        return True
    if kind_input == "morning":
        return False

    schedule = os.environ.get("GITHUB_EVENT_SCHEDULE")
    if schedule == EVENING_CRON:
        return True
    if schedule == MORNING_CRON:
        return False

    # 위 둘 다 없으면(예: 입력 없는 수동 실행) 현재 시각으로 판단
    return now.hour >= 14


def main() -> None:
    now = datetime.datetime.utcnow() + KST_OFFSET
    is_evening_run = _is_evening_run(now)

    if is_evening_run and now.hour < 12:
        # 자정을 넘겨서까지 지연된 저녁 실행: "오늘 저녁"은 사실 어제였다.
        represented_date = now.date() - datetime.timedelta(days=1)
    else:
        represented_date = now.date()

    target_offset = 1 if is_evening_run else 0
    kind = "evening_before" if is_evening_run else "morning_of"

    main_notices = fetch_all_notices()
    remainder_notices = fetch_all_remainder_notices()
    candidate_events = collect_candidate_events(main_notices, remainder_notices)

    # 먼저 날짜로 걸러낸다 (API 호출 없는 계산). 전용면적 확인(API 호출)은
    # 오늘/내일 접수인 소수의 후보에 대해서만, 그다음에 한다.
    matching_today = [e for e in candidate_events if (e["start_date"] - represented_date).days == target_offset]
    matching_today = [e for e in matching_today if passes_area_filter(e)]

    if not matching_today:
        _notify_no_notices(is_evening_run, represented_date)
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


def _notify_no_notices(is_evening_run: bool, represented_date: datetime.date) -> None:
    """접수 시작인, 조건에 맞는 공고가 하나도 없을 때 안내."""
    if is_evening_run:
        target_date = represented_date + datetime.timedelta(days=1)
        when_label = "내일"
        kind = "evening_before"
    else:
        target_date = represented_date
        when_label = "오늘"
        kind = "morning_of"
    empty_key = f"no-notices:{kind}:{target_date.isoformat()}"

    notified_ids = load_notified_ids()
    if empty_key in notified_ids:
        print(f"이미 안내함: {when_label}({target_date.isoformat()}) 해당 공고 없음")
        return

    send_message(f"[청약알림] {when_label}({target_date.isoformat()}) 접수 시작인, 조건에 맞는 서울 공고가 없습니다.")
    notified_ids.add(empty_key)
    save_notified_ids(notified_ids)
    print(f"알림 발송: {when_label}({target_date.isoformat()}) 해당 공고 없음")


if __name__ == "__main__":
    main()
