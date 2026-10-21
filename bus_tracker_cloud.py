"""
A-108 BEST Bus Tracker - Cloud Version (Railway / Render / Any VPS)
====================================================================
24/7 tracking - Telegram notifications only (no Windows popups needed)

Notifications:
  - RBI stop pe 5/4/3/2/1 min pehle Telegram message
  - Bus departure from Kamla Nehru Park
  - Walkeshwar & NCPA timestamps

Setup:
  Set environment variables OR edit TELEGRAM_* lines below.
  pip install requests
  python bus_tracker_cloud.py
"""

import time
import json
import sys
import os
from datetime import datetime
import pytz
import requests

try:
    from curl_cffi import requests as cffi_requests
    USE_CFFI = True
except ImportError:
    USE_CFFI = False

# =================================================================
#  OPERATING HOURS (IST)
# =================================================================
IST = pytz.timezone('Asia/Kolkata')

def is_operating_hours():
    """Sirf 9AM-2PM aur 4PM-6PM IST mein run karega"""
    now  = datetime.now(IST)
    mins = now.hour * 60 + now.minute
    morning = (9 * 60) <= mins <= (14 * 60)   # 9:00 AM – 2:00 PM IST
    evening = (16 * 60) <= mins <= (18 * 60)  # 4:00 PM – 6:00 PM IST
    return morning or evening

def current_window():
    now  = datetime.now(IST)
    mins = now.hour * 60 + now.minute
    if (9 * 60) <= mins <= (14 * 60):
        return "Morning (9AM–2PM IST)"
    if (16 * 60) <= mins <= (18 * 60):
        return "Evening (4PM–6PM IST)"
    return "Off Hours"


# =================================================================
#  *** SETTINGS - YAHAN BHARO (ya environment variable set karo) ***
# =================================================================

# Environment variables se lega (Railway/Render mein set karo)
# Ya seedha yahan paste karo:
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "YAHAN_BOT_TOKEN_DALO")
TELEGRAM_CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID",   "YAHAN_CHAT_ID_DALO")

# RBI pe kitne minute pehle alert chahiye
RBI_ALERT_AT_MINUTES        = [5, 4, 3, 2, 1]
WALKESHWAR_ALERT_AT_MINUTES = [5, 3, 1]

# =================================================================
#  INTERNAL CONFIG
# =================================================================

BASE_API          = "https://chalo.com/app/api/vasudha/track/route-live-info/mumbai"
LOG_FILE          = "bus_history_log.txt"
CHECK_SEC         = 30   # 15 ya 20 kar sakte ho faster checks ke liye
RBI_STOP_ID       = "UnxXKjiv"
WALKESHWAR_STOP_ID = "wkXXAyRN"

HEADERS = {
    "accept":             "application/json, text/plain, */*",
    "accept-language":    "en-US,en;q=0.9",
    "priority":           "u=1, i",
    "sec-ch-ua":          '"Google Chrome";v="125", "Chromium";v="125", "Not.A/Brand";v="24"',
    "sec-ch-ua-mobile":   "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest":     "empty",
    "sec-fetch-mode":     "cors",
    "sec-fetch-site":     "same-origin",
    "source":             "1",
    "user-agent":         "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
}

ORIGIN   = "origin"
TRACK    = "track"
KEYPOINT = "keypoint"

ROUTES = {
    "DOWN": {
        "label":    "[DOWN] A-108",
        "name":     "Kamla Nehru Park -> CST",
        "route_id": "HFYoziaE",
        "referer":  "https://chalo.com/app/live-tracking/route-map/HFYoziaE",
        "stops": [
            ("xDxjunCQ", "Kamla Nehru Park",        ORIGIN),
            ("BuVOALpO", "Sahyadri Guest House",     TRACK),
            ("SVwlFQzx", "Malabar Hill Post Office", TRACK),
            ("FOirkYKX", "Rekha Sadan Jain Mandir",  TRACK),
            ("wkXXAyRN", "Walkeshwar",               KEYPOINT),
        ],
    },
    "UP": {
        "label":    "[UP] A-108",
        "name":     "CST -> NCPA",
        "route_id": "iCUxIVjB",
        "referer":  "https://chalo.com/app/live-tracking/route-map/iCUxIVjB",
        "stops": [
            ("UnxXKjiv", "Reserve Bank of India",    TRACK),
            ("BKEWEwAL", "Old Custom House",         TRACK),
            ("ngIFMJQN", "Dr. S.P. Mukherji Chowk",  TRACK),
            ("EAGJZLSC", "Mantralaya",               TRACK),
            ("BxITZNDv", "NCPA",                     KEYPOINT),
        ],
    },
}


# =================================================================
#  TELEGRAM
# =================================================================

_telegram_ready = False

def check_telegram():
    global _telegram_ready
    if "YAHAN" in TELEGRAM_BOT_TOKEN or "YAHAN" in str(TELEGRAM_CHAT_ID):
        print("[!] Telegram not configured - set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID")
        return
    try:
        resp = requests.get(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getMe",
            timeout=10
        )
        if resp.status_code == 200:
            bot_name = resp.json().get("result", {}).get("username", "?")
            print(f"[OK] Telegram ready - @{bot_name}")
            _telegram_ready = True
        else:
            print(f"[!] Telegram auth failed - HTTP {resp.status_code}")
    except Exception as e:
        print(f"[!] Telegram error: {e}")


def send_telegram(message: str, silent: bool = False):
    if not _telegram_ready:
        return False
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            data={
                "chat_id":              TELEGRAM_CHAT_ID,
                "text":                 message,
                "parse_mode":           "HTML",
                "disable_notification": silent,
            },
            timeout=10,
        )
        return resp.status_code == 200
    except Exception as e:
        print(f"  [!] Telegram send error: {e}")
        return False


# =================================================================
#  LOGGING
# =================================================================

def log(line: str):
    ts   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    full = f"[{ts}] {line}"
    print(full)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(full + "\n")
    except Exception:
        pass


# =================================================================
#  STATE
# =================================================================

bus_state    = {}
_first_cycle = {"DOWN": True, "UP": True}


# =================================================================
#  API
# =================================================================

def build_url(cfg: dict) -> str:
    ids = ",".join(s[0] for s in cfg["stops"])
    return f"{BASE_API}/{cfg['route_id']}?stopIds={ids}"


_session = None

def get_session():
    global _session
    if _session is None:
        if USE_CFFI:
            _session = cffi_requests.Session(impersonate="chrome124")
        else:
            _session = requests.Session()
    return _session

def fetch(route_key: str):
    s = get_session()
    cfg  = ROUTES[route_key]
    hdrs = {**HEADERS, "referer": cfg["referer"]}
    try:
        r = s.get(build_url(cfg), headers=hdrs, timeout=15)
        if r.status_code == 200:
            return r.json()
        log(f"API HTTP {r.status_code} for {route_key} | {r.text[:120]}")
    except Exception as e:
        log(f"Fetch error - {route_key} - {e}")
    return None


# =================================================================
#  TRACKING ENGINE
# =================================================================

def process(route_key: str, data: dict):
    cfg        = ROUTES[route_key]
    stops_eta  = data.get("stopsEta", {})
    stop_map   = {s[0]: (s[1], s[2]) for s in cfg["stops"]}
    origin_def = next((s for s in cfg["stops"] if s[2] == ORIGIN), None)

    now      = datetime.now()
    ts_short = now.strftime("%H:%M:%S")
    ts_full  = now.strftime("%Y-%m-%d %H:%M:%S")

    all_bus_keys = set()
    for sid in stop_map:
        if sid in stops_eta:
            all_bus_keys.update(stops_eta[sid].keys())

    any_active = False

    for bk in sorted(all_bus_keys):
        uid = f"{route_key}_{bk}"

        per_stop = {}
        vNo = "?"
        for sid in stop_map:
            if sid not in stops_eta or bk not in stops_eta[sid]:
                continue
            raw = stops_eta[sid][bk]
            try:
                info = json.loads(raw) if isinstance(raw, str) else raw
            except Exception:
                continue
            per_stop[sid] = info
            vNo = info.get("vNo", vNo)

        if not per_stop:
            continue

        if uid not in bus_state:
            bus_state[uid] = {
                "vNo":                  vNo,
                "rbi_telegram":         set(),
                "walkeshwar_telegram":  set(),
                "prev_eta":             {},
                "timestamps":           {},
                "departed_origin":      False,
            }

        st        = bus_state[uid]
        st["vNo"] = vNo

        # ---- 1) DEPARTURE DETECTION ----------------------------
        if origin_def and not st["departed_origin"]:
            origin_id, origin_name, _ = origin_def
            origin_info  = per_stop.get(origin_id)
            later_active = any(
                per_stop[sid].get("eta", -1) > 0
                for sid in per_stop if sid != origin_id
            )
            if later_active and (origin_info is None
                                  or origin_info.get("eta", -1) <= 0):
                st["departed_origin"] = True
                if not _first_cycle[route_key]:
                    msg = (f"<b>Bus Nikli!</b>\n"
                           f"Bus <b>{vNo}</b> - {origin_name} se nikal chuki hai\n"
                           f"Route: {cfg['name']}\n"
                           f"Time: {ts_short}")
                    send_telegram(msg)
                    log(f"DEPARTURE | {cfg['name']} | Bus {vNo} | {origin_name}")

        # ---- 2) PER-STOP PROCESSING ----------------------------
        for sid, (sname, stype) in stop_map.items():
            if sid not in per_stop:
                continue

            info    = per_stop[sid]
            eta_sec = info.get("eta", -1)
            dist    = info.get("dist", 0)
            prev    = st["prev_eta"].get(sid)

            # A) Bus approaching
            if eta_sec > 0:
                any_active = True
                eta_min    = round(eta_sec / 60, 1)

                prev_min = round(prev / 60, 1) if prev and prev > 0 else None
                if prev_min is None or abs(prev_min - eta_min) >= 0.5:
                    log(f"ETA | {cfg['name']} | Bus {vNo} | "
                        f"{sname} | {eta_min}min | {dist}m")

                # Telegram alerts - RBI stop
                if sid == RBI_STOP_ID and not _first_cycle[route_key]:
                    for m in RBI_ALERT_AT_MINUTES:
                        if m in st["rbi_telegram"]:
                            continue
                        if eta_min <= m:
                            if m <= 1:
                                urgency = "ABHI NIKLO!"
                                emoji   = "URGENT"
                            elif m <= 2:
                                urgency = "Jaldi karo!"
                                emoji   = "ALERT"
                            elif m <= 3:
                                urgency = "Chalte chalte taiyar ho jao"
                                emoji   = "SOON"
                            else:
                                urgency = "Taiyar ho jao"
                                emoji   = "INFO"

                            tg_msg = (
                                f"[{emoji}] A-108 Bus Alert!\n"
                                f"\n"
                                f"Bus: <b>{vNo}</b>\n"
                                f"Stop: <b>Reserve Bank of India</b>\n"
                                f"ETA: <b>{eta_min} min</b> ({dist}m door)\n"
                                f"Route: {cfg['name']}\n"
                                f"Time: {ts_short}\n"
                                f"\n"
                                f"<b>{urgency}</b>"
                            )
                            ok = send_telegram(tg_msg)
                            log(f"TELEGRAM {'OK' if ok else 'FAIL'} | "
                                f"Bus {vNo} | RBI | {m}min alert")
                            for m2 in RBI_ALERT_AT_MINUTES:
                                if m2 >= m:
                                    st["rbi_telegram"].add(m2)
                            break

                # Telegram alerts - Walkeshwar stop
                if sid == WALKESHWAR_STOP_ID and not _first_cycle[route_key]:
                    for m in WALKESHWAR_ALERT_AT_MINUTES:
                        if m in st["walkeshwar_telegram"]:
                            continue
                        if eta_min <= m:
                            if m <= 1:
                                urgency = "ABHI PAHUCHNE WALI HAI!"
                                emoji   = "URGENT"
                            elif m <= 3:
                                urgency = "Bas thodi der mein!"
                                emoji   = "SOON"
                            else:
                                urgency = "Bus aa rahi hai"
                                emoji   = "INFO"

                            tg_msg = (
                                f"[{emoji}] A-108 Walkeshwar Alert!\n"
                                f"\n"
                                f"Bus: <b>{vNo}</b>\n"
                                f"Stop: <b>Walkeshwar</b>\n"
                                f"ETA: <b>{eta_min} min</b> ({dist}m door)\n"
                                f"Route: {cfg['name']}\n"
                                f"Time: {ts_short}\n"
                                f"\n"
                                f"<b>{urgency}</b>"
                            )
                            ok = send_telegram(tg_msg)
                            log(f"TELEGRAM {'OK' if ok else 'FAIL'} | "
                                f"Bus {vNo} | Walkeshwar | {m}min alert")
                            for m2 in WALKESHWAR_ALERT_AT_MINUTES:
                                if m2 >= m:
                                    st["walkeshwar_telegram"].add(m2)
                            break

                st["prev_eta"][sid] = eta_sec

            # B) Bus passed this stop
            elif prev is not None and prev > 0 and eta_sec <= 0:
                st["prev_eta"][sid] = eta_sec

                if stype == KEYPOINT:
                    st["timestamps"][sid] = ts_short
                    send_telegram(
                        f"<b>Timestamp</b>\n"
                        f"Bus <b>{vNo}</b> - {sname}\n"
                        f"Pahunchi / Nikli @ <b>{ts_short}</b>\n"
                        f"Route: {cfg['name']}"
                    )
                    log(f"TIMESTAMP | {cfg['name']} | Bus {vNo} | {sname} @ {ts_short}")

                elif sid == RBI_STOP_ID and not _first_cycle[route_key]:
                    send_telegram(
                        f"Bus <b>{vNo}</b> Reserve Bank of India se nikal gayi\n"
                        f"Time: {ts_short}"
                    )
                    log(f"PASSED | Bus {vNo} | RBI crossed @ {ts_short}")
                else:
                    log(f"PASSED | {cfg['name']} | Bus {vNo} | {sname}")
            else:
                st["prev_eta"][sid] = eta_sec

    if not any_active:
        print(f"  [{datetime.now().strftime('%H:%M:%S')}] "
              f"{cfg['label']} - koi bus range mein nahi")

    _first_cycle[route_key] = False

    prefix = f"{route_key}_"
    stale  = [u for u in bus_state
              if u.startswith(prefix)
              and u.split("_", 1)[1] not in all_bus_keys]
    for u in stale:
        del bus_state[u]


# =================================================================
#  MAIN
# =================================================================

def main():
    # ---- Operating hours check ----
    now_ist = datetime.now(IST)
    if not is_operating_hours():
        print(f"[{now_ist.strftime('%H:%M IST')}] Operating hours ke bahar hai.")
        print("Tracker chalega: 9AM-2PM IST | 4PM-6PM IST")
        sys.exit(0)

    print()
    print("=" * 60)
    print("  A-108 Bus Tracker - CLOUD VERSION (GitHub Actions)")
    print(f"  Window  : {current_window()}")
    print("=" * 60)
    for rk, rc in ROUTES.items():
        print(f"  {rc['label']}: {rc['name']}  ({len(rc['stops'])} stops)")
    print(f"  RBI Telegram alerts : {RBI_ALERT_AT_MINUTES} min before")
    print(f"  Check interval      : {CHECK_SEC}s")
    check_telegram()
    print("=" * 60)
    print("  (First cycle silent - learning existing buses)")
    print()

    cycle = 0
    while True:
        # ---- Stop when operating hours end ----
        if not is_operating_hours():
            log(f"Operating hours khatam ({current_window()}) - tracker band ho raha hai.")
            sys.exit(0)

        cycle += 1
        print(f"\n--- Cycle #{cycle} @ "
              f"{datetime.now(IST).strftime('%H:%M:%S IST')} ---")
        for rk in ["DOWN", "UP"]:
            data = fetch(rk)
            if data:
                process(rk, data)
        time.sleep(CHECK_SEC)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nTracker stopped.")
        sys.exit(0)
