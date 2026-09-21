#!/usr/bin/env python3
"""
스플래툰 3 맵·룰 디스코드 알림 봇
데이터 출처: Splatoon3.ink (https://splatoon3.ink) - 닌텐도 공식 서비스가 아닌 팬 사이트
"""
import json
import os
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

# ============ 설정 (알림 조건을 바꾸고 싶으면 여기만 고치면 돼요) ============
TARGET_STAGE_ID = "VnNTdGFnZS0xMg=="  # 만새기 리조트＆스파
TARGET_RULE_ID = "VnNSdWxlLTQ="        # 랭크 바지락
TARGET_MODE = "OPEN"                   # OPEN = 오픈, CHALLENGE = 챌린지

REMIND_WINDOW_MIN = 20   # 시작까지 이 시간(분) 이하로 남으면 '곧 시작' 알림
FETCH_INTERVAL_MIN = 55  # 데이터는 한 시간에 한 번만 받기 (Splatoon3.ink 요청 사항)
# ==========================================================================

SCHEDULE_URL = "https://splatoon3.ink/data/schedules.json"
LOCALE_URL = "https://splatoon3.ink/data/locale/ko-KR.json"
STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state.json")

KST = timezone(timedelta(hours=9))
WEEKDAYS = ["월", "화", "수", "목", "금", "토", "일"]
MODE_LABEL = {"OPEN": "오픈", "CHALLENGE": "챌린지"}

REPO = os.environ.get("GITHUB_REPOSITORY", "personal-use")
USER_AGENT = f"splat-map-alert/1.0 (+https://github.com/{REPO})"


# ---------- 공통 도구 ----------
def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=20) as res:
        return json.loads(res.read().decode("utf-8"))


def parse_time(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def fmt_kst(dt):
    k = dt.astimezone(KST)
    return f"{k.month}/{k.day}({WEEKDAYS[k.weekday()]}) {k:%H:%M}"


def fmt_duration(minutes):
    minutes = max(0, int(round(minutes)))
    h, m = divmod(minutes, 60)
    if h and m:
        return f"{h}시간 {m}분"
    if h:
        return f"{h}시간"
    return f"{m}분"


def send_discord(content):
    if os.environ.get("DRY_RUN"):
        print("[DRY_RUN] 디스코드로 보낼 메시지:\n" + content + "\n")
        return True
    url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not url:
        print("오류: DISCORD_WEBHOOK_URL이 설정되지 않았어요.")
        return False
    body = json.dumps({"username": "스플래툰 맵 알림", "content": content}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json", "User-Agent": USER_AGENT},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as res:
            return 200 <= res.status < 300
    except Exception as e:
        print(f"디스코드 전송 실패: {e}")
        return False


def load_state():
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"fetched_at": None, "matches": [], "sent": {}}


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")


# ---------- 스케줄에서 원하는 조합 찾기 ----------
def find_matches(schedules, locale):
    stage_names = {k: v.get("name") for k, v in (locale.get("stages") or {}).items()}
    rule_names = {k: v.get("name") for k, v in (locale.get("rules") or {}).items()}

    nodes = (((schedules.get("data") or {}).get("bankaraSchedules") or {}).get("nodes")) or []
    matches = []
    for node in nodes:
        # 페스티벌 기간 등에는 이 값이 비어 있을 수 있어요
        for s in node.get("bankaraMatchSettings") or []:
            if s.get("bankaraMode") != TARGET_MODE:
                continue
            rule = s.get("vsRule") or {}
            if rule.get("id") != TARGET_RULE_ID:
                continue
            stages = s.get("vsStages") or []
            ids = [st.get("id") for st in stages]
            if TARGET_STAGE_ID not in ids:
                continue
            names = [stage_names.get(st.get("id")) or st.get("name") or "?" for st in stages]
            target_name = stage_names.get(TARGET_STAGE_ID) or "목표 맵"
            matches.append({
                "start": node["startTime"],
                "end": node["endTime"],
                "target_stage": target_name,
                "other_stages": [n for n in names if n != target_name],
                "rule": rule_names.get(TARGET_RULE_ID) or rule.get("name") or "목표 룰",
            })
    return matches


# ---------- 메시지 만들기 ----------
def build_message(kind, m, now):
    start, end = parse_time(m["start"]), parse_time(m["end"])
    title = f"{m['target_stage']} · {m['rule']} ({MODE_LABEL.get(TARGET_MODE, TARGET_MODE)})"
    others = ", ".join(m["other_stages"]) or "-"
    time_line = f"📅 {fmt_kst(start)} ~ {end.astimezone(KST):%H:%M}"
    until = (start - now).total_seconds() / 60
    left = (end - now).total_seconds() / 60

    if kind == "found":
        head = f"🦑 **{title}** 일정이 잡혔어요!"
        status = f"⏳ 약 {fmt_duration(until)} 후 시작"
    elif kind == "soon":
        head = f"⏰ **{title}** 곧 시작해요!"
        status = f"⏳ {fmt_duration(until)} 후 시작"
    elif kind == "now":
        head = f"🔥 **{title}** 지금 진행 중이에요!"
        status = f"⏳ 끝나기까지 {fmt_duration(left)}"
    else:  # started (예약 실행이 늦어져서 시작 전 알림을 놓친 경우)
        head = f"▶️ **{title}** 방금 시작했어요! (알림이 조금 늦었어요)"
        status = f"⏳ 끝나기까지 {fmt_duration(left)}"

    return "\n".join([head, time_line, status, f"🗺️ 함께 나오는 맵: {others}"])


# ---------- 메인 ----------
def main():
    if os.environ.get("TEST_MESSAGE"):
        ok = send_discord("✅ 스플래툰 맵 알림 봇 연결 테스트예요. 이 메시지가 보이면 설정 완료!")
        print("테스트 메시지 전송", "성공" if ok else "실패")
        sys.exit(0 if ok else 1)

    now = datetime.now(timezone.utc)
    if os.environ.get("NOW"):  # 테스트용
        now = parse_time(os.environ["NOW"])

    state = load_state()
    before = json.dumps(state, sort_keys=True, ensure_ascii=False)

    # 1) 한 시간에 한 번만 새 데이터 받기
    fetched_at = parse_time(state["fetched_at"]) if state.get("fetched_at") else None
    if fetched_at is None or now - fetched_at >= timedelta(minutes=FETCH_INTERVAL_MIN):
        try:
            schedules = get_json(SCHEDULE_URL)
            locale = get_json(LOCALE_URL)
            state["matches"] = find_matches(schedules, locale)
            state["fetched_at"] = now.isoformat()
            print(f"데이터 갱신 완료: 조건에 맞는 일정 {len(state['matches'])}개")
        except Exception as e:
            print(f"데이터를 받지 못했어요 (저장된 정보로 계속 진행): {e}")
    else:
        print("최근에 받은 데이터를 사용해요.")

    # 2) 알림 판단
    sent = state.setdefault("sent", {})
    for m in sorted(state.get("matches", []), key=lambda x: x["start"]):
        start, end = parse_time(m["start"]), parse_time(m["end"])
        if end <= now:
            continue
        rec = sent.setdefault(m["start"], {"found": False, "remind": False})
        until = (start - now).total_seconds() / 60

        if not rec["found"]:
            if start <= now:
                kind = "now"
            elif until <= REMIND_WINDOW_MIN:
                kind = "soon"
            else:
                kind = "found"
            if send_discord(build_message(kind, m, now)):
                rec["found"] = True
                if kind in ("now", "soon"):
                    rec["remind"] = True
        elif not rec["remind"]:
            kind = None
            if 0 < until <= REMIND_WINDOW_MIN:
                kind = "soon"
            elif start <= now:
                kind = "started"
            if kind and send_discord(build_message(kind, m, now)):
                rec["remind"] = True

    # 3) 끝난 일정 정리
    state["matches"] = [m for m in state.get("matches", []) if parse_time(m["end"]) > now]
    cutoff = now - timedelta(days=2)
    state["sent"] = {k: v for k, v in sent.items() if parse_time(k) > cutoff}

    if json.dumps(state, sort_keys=True, ensure_ascii=False) != before:
        save_state(state)


if __name__ == "__main__":
    main()
