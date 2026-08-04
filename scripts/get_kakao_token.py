"""
카카오톡 "나에게 보내기"용 최초 access_token / refresh_token 발급 스크립트.

사전 준비 (https://developers.kakao.com):
1. 애플리케이션 생성 후 "앱 키 > REST API 키" 확인 (KAKAO_REST_API_KEY로 사용)
2. 제품설정 > 카카오 로그인 > 활성화 설정 ON
3. 제품설정 > 카카오 로그인 > Redirect URI에 이 스크립트에서 쓸 주소를 등록
   (예: http://localhost:5000 — 실제로 그 주소가 떠 있을 필요는 없음)
4. 제품설정 > 카카오 로그인 > 동의항목에서 "카카오톡 메시지 전송"(talk_message) 활성화
   (권장 상태가 아니면 검수 없이도 개발 단계에서 본인 계정으로는 사용 가능)
5. 앱설정 > 앱 > 고급 > "클라이언트 시크릿"에서 "카카오 로그인" 코드가
   활성화(ON) 상태라면 그 코드 값도 준비해둘 것 (KAKAO_CLIENT_SECRET)

사용법:
    python scripts/get_kakao_token.py

절차:
1. 스크립트가 출력하는 인가 URL을 브라우저에서 열어 카카오 로그인 + 동의를 진행한다.
2. 로그인 후 Redirect URI로 이동하며 주소창에 `?code=...`가 붙는다
   (그 페이지 자체는 안 열려도 상관없다). code= 뒤의 값을 복사한다.
3. 터미널에 그 코드를 붙여넣으면 access_token/refresh_token으로 교환해 출력한다.
4. 출력된 KAKAO_REFRESH_TOKEN 값을 GitHub 저장소 Settings > Secrets and
   variables > Actions 에 등록한다.
"""
import os
import sys
import urllib.parse

import requests

AUTH_URL = "https://kauth.kakao.com/oauth/authorize"
TOKEN_URL = "https://kauth.kakao.com/oauth/token"
DEFAULT_REDIRECT_URI = "http://localhost:5000"


def main() -> None:
    rest_api_key = os.environ.get("KAKAO_REST_API_KEY") or input("카카오 REST API 키: ").strip()
    redirect_uri = (
        os.environ.get("KAKAO_REDIRECT_URI")
        or input(f"Redirect URI (카카오 개발자센터에 등록한 값, 기본값 {DEFAULT_REDIRECT_URI}): ").strip()
        or DEFAULT_REDIRECT_URI
    )
    client_secret = os.environ.get("KAKAO_CLIENT_SECRET") or input(
        "Client Secret (앱설정 > 앱 > 고급 > 클라이언트 시크릿에서 \"카카오 로그인\"이"
        " 활성화 상태일 때만 입력, 아니면 그냥 엔터): "
    ).strip()

    auth_params = {
        "client_id": rest_api_key,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "talk_message",
    }
    auth_url = f"{AUTH_URL}?{urllib.parse.urlencode(auth_params)}"

    print("\n1) 아래 URL을 브라우저에서 열어 카카오 로그인 후 동의하세요:")
    print(auth_url)
    print(
        f"\n2) 로그인이 끝나면 브라우저가 {redirect_uri}?code=... 로 이동합니다"
        " (그 페이지가 안 열려도 정상입니다). 주소창에서 code= 뒤의 값을 복사하세요."
    )

    code = input("\n인가 코드(code): ").strip()
    if not code:
        print("인가 코드가 입력되지 않았습니다.", file=sys.stderr)
        sys.exit(1)

    token_data = {
        "grant_type": "authorization_code",
        "client_id": rest_api_key,
        "redirect_uri": redirect_uri,
        "code": code,
    }
    if client_secret:
        token_data["client_secret"] = client_secret

    resp = requests.post(TOKEN_URL, data=token_data, timeout=15)
    if not resp.ok:
        print(f"토큰 교환 실패 ({resp.status_code}): {resp.text}", file=sys.stderr)
        sys.exit(1)
    token = resp.json()

    print("\n발급 완료. 아래 값을 GitHub 저장소 Settings > Secrets and variables > Actions 에 등록하세요:")
    print(f"  KAKAO_REST_API_KEY = {rest_api_key}")
    print(f"  KAKAO_REFRESH_TOKEN = {token['refresh_token']}")
    if client_secret:
        print(f"  KAKAO_CLIENT_SECRET = {client_secret}")
    print(f"\n(access_token은 6시간 후 만료되며 별도로 저장할 필요는 없습니다.)")


if __name__ == "__main__":
    main()
