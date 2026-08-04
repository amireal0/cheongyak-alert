"""이미 알림을 보낸 공고 ID를 state.json에 기록해 중복 알림을 방지."""
import json
import os

STATE_PATH = os.path.join(os.path.dirname(__file__), "..", "state.json")


def load_notified_ids() -> set[str]:
    if not os.path.exists(STATE_PATH):
        return set()
    with open(STATE_PATH, "r", encoding="utf-8") as f:
        return set(json.load(f))


def save_notified_ids(ids: set[str]) -> None:
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(sorted(ids), f, ensure_ascii=False, indent=2)
