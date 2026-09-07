"""카카오가 access_token 갱신 응답에 새 refresh_token을 함께 내려주면(유효기간이
얼마 안 남았을 때 자동으로 그렇게 함), 그 값을 GitHub Actions Secret
(KAKAO_REFRESH_TOKEN)에 자동으로 다시 저장한다.

이게 없으면 최초 발급받은 refresh_token 하나로 계속 버티다가 카카오 정책상
만료 시점(최대 60일)에 알림이 한꺼번에 끊긴다. 매 실행마다 새로 온 토큰을
Secret에 반영해두면, 이 워크플로우가 계속 도는 한 refresh_token이 스스로
갱신되어 사실상 만료되지 않는다.

Actions가 실행마다 자동 발급하는 GITHUB_TOKEN은 Secrets를 고쳐 쓸 권한이 없어서,
별도로 발급해 등록해둔 GH_SECRETS_PAT(이 저장소의 "Secrets: Read and write"
권한만 있는 fine-grained PAT)를 사용한다. 이 PAT 자체도 언젠가 만료되지만,
GitHub가 만료 전에 이메일로 미리 알려주므로 카카오 토큰처럼 조용히 끊기지 않는다.
"""
import base64
import os

import requests
from nacl import encoding, public

GITHUB_API = "https://api.github.com"
SECRET_NAME = "KAKAO_REFRESH_TOKEN"


def _encrypt(public_key_b64: str, secret_value: str) -> str:
    public_key = public.PublicKey(public_key_b64.encode("utf-8"), encoding.Base64Encoder())
    sealed_box = public.SealedBox(public_key)
    encrypted = sealed_box.encrypt(secret_value.encode("utf-8"))
    return base64.b64encode(encrypted).decode("utf-8")


def update_refresh_token_secret(new_refresh_token: str) -> None:
    pat = os.environ.get("GH_SECRETS_PAT")
    repo = os.environ.get("GITHUB_REPOSITORY")
    if not pat or not repo:
        print("GH_SECRETS_PAT 또는 GITHUB_REPOSITORY 없음: 새 리프레시 토큰을 "
              "Secret에 자동 저장하지 못함 (그대로 두면 다음 만료 때 수동 재발급 필요)")
        return

    headers = {
        "Authorization": f"Bearer {pat}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    key_resp = requests.get(
        f"{GITHUB_API}/repos/{repo}/actions/secrets/public-key", headers=headers, timeout=15
    )
    key_resp.raise_for_status()
    key_data = key_resp.json()

    encrypted_value = _encrypt(key_data["key"], new_refresh_token)

    put_resp = requests.put(
        f"{GITHUB_API}/repos/{repo}/actions/secrets/{SECRET_NAME}",
        headers=headers,
        json={"encrypted_value": encrypted_value, "key_id": key_data["key_id"]},
        timeout=15,
    )
    put_resp.raise_for_status()
    print(f"{SECRET_NAME} 시크릿을 새로 발급된 리프레시 토큰으로 자동 갱신함")
