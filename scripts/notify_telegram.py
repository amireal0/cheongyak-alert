"""텔레그램 봇으로 알림 발송.

사전에 @BotFather 로 봇을 만들어 TELEGRAM_BOT_TOKEN 을, 봇과 대화를 시작한 뒤
getUpdates 로 확인한 chat id 를 TELEGRAM_CHAT_ID 로 환경변수/시크릿에 등록해야 합니다.
"""
import os
import requests

SEND_URL = "https://api.telegram.org/bot{token}/sendMessage"
MAX_LEN = 4096  # 텔레그램 메시지 글자수 제한


def _split(text: str) -> list[str]:
    """제한을 넘으면 빈 줄(공고 블록) 단위로 나눈다."""
    if len(text) <= MAX_LEN:
        return [text]
    chunks, current = [], ""
    for block in text.split("\n\n"):
        candidate = f"{current}\n\n{block}" if current else block
        if len(candidate) > MAX_LEN and current:
            chunks.append(current)
            current = block
        else:
            current = candidate
    if current:
        chunks.append(current)
    return [c[:MAX_LEN] for c in chunks]


def send_message(text: str) -> None:
    url = SEND_URL.format(token=os.environ["TELEGRAM_BOT_TOKEN"])
    for chunk in _split(text):
        try:
            resp = requests.post(
                url,
                json={
                    "chat_id": os.environ["TELEGRAM_CHAT_ID"],
                    "text": chunk,
                    "disable_web_page_preview": True,
                },
                timeout=15,
            )
        except requests.exceptions.RequestException as exc:
            # 예외 메시지에 토큰이 든 URL이 그대로 들어가므로 로그에 안 남도록 가린다.
            raise RuntimeError(f"텔레그램 발송 실패(네트워크): {type(exc).__name__}") from None
        if not resp.ok:
            raise RuntimeError(f"텔레그램 발송 실패 ({resp.status_code}): {resp.text}")


def _event_block(event: dict) -> str:
    """공급유형 하나(특별공급/1순위/2순위/무순위/불법행위재공급)에 대한 문구 블록.

    형식: 공급유형 구분 / 주택명(지역) / 청약접수일 / 접수 사이트.
    """
    notice = event["notice"]
    name = notice.get("HOUSE_NM") or "이름 미상"
    region = notice.get("SUBSCRPT_AREA_CODE_NM") or ""
    type_label = event["type_label"]
    start = event["start_date"].isoformat()
    end = event["end_date"].isoformat()
    url = notice.get("PBLANC_URL") or "https://www.applyhome.co.kr"
    return f"[{type_label}] {name} ({region})\n접수기간: {start}~{end}\n{url}"


def build_message(events: list[dict]) -> str:
    """한 회차에 조건에 맞은 공고 이벤트를 모두 하나의 메시지로 묶는다."""
    header = f"[청약알림] 조건에 맞는 공고 {len(events)}건"
    blocks = [_event_block(e) for e in events]
    return header + "\n\n" + "\n\n".join(blocks)
