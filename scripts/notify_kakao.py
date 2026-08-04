"""카카오톡 '나에게 보내기' API로 알림 발송.

사전에 카카오 개발자센터에서 앱 등록 + 카카오 로그인(메시지 전송 동의)을
거쳐 refresh_token을 발급받아 KAKAO_REFRESH_TOKEN 환경변수/시크릿으로
등록해두어야 합니다. 앱의 "카카오 로그인 > 보안" 설정에서 Client Secret이
활성화되어 있다면 KAKAO_CLIENT_SECRET 환경변수/시크릿도 등록해야 합니다
(비활성화된 앱이라면 비워둬도 됩니다).
"""
import json
import os
import requests

TOKEN_URL = "https://kauth.kakao.com/oauth/token"
SEND_URL = "https://kapi.kakao.com/v2/api/talk/memo/default/send"


def _refresh_access_token() -> str:
    data = {
        "grant_type": "refresh_token",
        "client_id": os.environ["KAKAO_REST_API_KEY"],
        "refresh_token": os.environ["KAKAO_REFRESH_TOKEN"],
    }
    client_secret = os.environ.get("KAKAO_CLIENT_SECRET")
    if client_secret:
        data["client_secret"] = client_secret

    resp = requests.post(TOKEN_URL, data=data, timeout=15)
    resp.raise_for_status()
    return resp.json()["access_token"]


def send_message(text: str, url: str = "https://www.applyhome.co.kr") -> None:
    access_token = _refresh_access_token()
    template = {
        "object_type": "text",
        "text": text,
        "link": {"web_url": url, "mobile_web_url": url},
    }
    resp = requests.post(
        SEND_URL,
        headers={"Authorization": f"Bearer {access_token}"},
        data={"template_object": json.dumps(template, ensure_ascii=False)},
        timeout=15,
    )
    resp.raise_for_status()


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
    """한 회차에 조건에 맞은 공고 이벤트를 모두 하나의 메시지로 묶는다.
    카카오 텍스트 템플릿에 실측된 글자수 제한은 없음을 확인함(395자 정상 수신).
    """
    header = f"[청약알림] 조건에 맞는 공고 {len(events)}건"
    blocks = [_event_block(e) for e in events]
    return header + "\n\n" + "\n\n".join(blocks)
