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


def send_message(text: str) -> None:
    access_token = _refresh_access_token()
    template = {
        "object_type": "text",
        "text": text[:200],
        "link": {"web_url": "https://www.applyhome.co.kr", "mobile_web_url": "https://www.applyhome.co.kr"},
    }
    resp = requests.post(
        SEND_URL,
        headers={"Authorization": f"Bearer {access_token}"},
        data={"template_object": json.dumps(template, ensure_ascii=False)},
        timeout=15,
    )
    resp.raise_for_status()


def build_message(notices: list[dict]) -> str:
    lines = [f"[청약 알림] 조건에 맞는 공고 {len(notices)}건"]
    for n in notices[:10]:
        name = n.get("HOUSE_NM") or "이름 미상"
        area = n.get("SUBSCRPT_AREA_CODE_NM") or ""
        lines.append(f"- {name} ({area})")
    return "\n".join(lines)
