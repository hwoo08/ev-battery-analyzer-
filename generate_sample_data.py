#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
입고 배터리 샘플 데이터 생성기

data/incoming_batteries.csv 를 만듭니다.

⚠️ 여기서 만들어지는 데이터는 실제 차량에서 수집한 값이 아니라
   합성(synthetic) 데이터입니다. 실 데이터를 구하기 전까지 판정 로직과
   대시보드를 검증하기 위한 용도이며, 어떤 규칙으로 만들었는지
   투명하게 남기려고 이 스크립트를 저장소에 함께 둡니다.

생성 규칙 (실제 배터리 열화 경향을 단순화해 반영)
  · 사용기간과 주행거리가 늘수록 SOH가 낮아진다
  · 급속충전 비율이 높을수록 SOH가 조금 더 낮아진다
  · SOH가 낮은 팩일수록 셀 전압 편차와 BMS 오류가 커지는 경향이 있다
  · 소수의 팩은 온도 이상·BMS 이상 등 안전 문제를 가진다

실행:
    python3 tools/generate_sample_data.py
"""

import csv
import os
import random

SEED = 20260827          # EV트렌드코리아 2026 방문일 — 재현 가능하도록 고정
COUNT = 120

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_PATH = os.path.join(BASE_DIR, "data", "incoming_batteries.csv")

MODELS = [
    ("EV A", 64.0),
    ("EV B", 77.4),
    ("EV C", 58.0),
    ("EV D", 84.0),
    ("EV E", 72.6),
]

FIELDS = [
    "battery_id", "vehicle", "pack_capacity_kwh", "usage_years", "mileage_km",
    "soh_percent", "avg_temp_c", "max_temp_c", "cell_v_max", "cell_v_min",
    "bms_error_count", "fast_charge_ratio_percent",
]


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def make_battery(index, rng):
    vehicle, capacity = rng.choice(MODELS)

    usage_years = round(rng.uniform(1.0, 13.0), 1)
    # 연간 주행거리는 차량마다 다르므로 폭을 두고 뽑습니다
    km_per_year = rng.uniform(8000, 24000)
    mileage_km = int(usage_years * km_per_year)

    fast_charge_ratio = round(clamp(rng.gauss(40, 18), 5, 95), 0)

    # --- SOH: 연식·주행거리·급속충전이 클수록 낮아짐 ---------------
    age_loss = usage_years * 2.2
    mileage_loss = mileage_km / 160000 * 17.0
    fast_loss = (fast_charge_ratio - 40) / 100 * 8.0
    noise = rng.gauss(0, 2.5)
    soh = clamp(100 - age_loss - mileage_loss - fast_loss + noise, 35.0, 99.5)

    # --- 셀 전압 편차: SOH가 낮을수록 벌어짐 -----------------------
    deviation_mv = clamp(rng.gauss((100 - soh) * 1.4, 12), 5, 260)

    # --- 온도 이력 -------------------------------------------------
    avg_temp = round(clamp(rng.gauss(29, 4), 18, 46), 1)
    max_temp = round(clamp(avg_temp + rng.uniform(9, 22), avg_temp + 5, 78), 1)

    # --- BMS 오류: SOH가 낮을수록 잦음 -----------------------------
    error_lambda = max(0.0, (85 - soh) / 12)
    bms_errors = min(int(rng.expovariate(1 / (error_lambda + 0.35))), 14)

    # --- 소수의 안전 이상 케이스를 의도적으로 섞음 -----------------
    roll = rng.random()
    if roll < 0.06:                       # 열 이상
        max_temp = round(rng.uniform(62, 78), 1)
    elif roll < 0.11:                     # 셀 밸런싱 이상
        deviation_mv = rng.uniform(105, 260)
    elif roll < 0.15:                     # BMS 다발 오류
        bms_errors = rng.randint(6, 14)

    # 편차(mV)를 실제 셀 전압 두 개로 되돌립니다
    v_max = round(rng.uniform(4.05, 4.14), 3)
    v_min = round(v_max - deviation_mv / 1000.0, 3)

    return {
        "battery_id": f"IN-2026-{index:03d}",
        "vehicle": vehicle,
        "pack_capacity_kwh": capacity,
        "usage_years": usage_years,
        "mileage_km": mileage_km,
        "soh_percent": round(soh, 1),
        "avg_temp_c": avg_temp,
        "max_temp_c": max_temp,
        "cell_v_max": v_max,
        "cell_v_min": v_min,
        "bms_error_count": bms_errors,
        "fast_charge_ratio_percent": int(fast_charge_ratio),
    }


def write_js(rows, path):
    """
    웹 대시보드용 JS 파일.

    브라우저에서 CSV를 fetch()로 읽으면 파일을 더블클릭해 열었을 때
    (file:// 주소) 브라우저 보안 정책에 막혀 동작하지 않습니다.
    그래서 같은 데이터를 JS 변수로도 내보내 로컬·웹 양쪽에서 동작하게 합니다.
    """
    import json
    with open(path, "w", encoding="utf-8") as f:
        f.write("/* 자동 생성 파일 — 직접 수정하지 마세요.\n")
        f.write("   tools/generate_sample_data.py 를 실행하면 다시 만들어집니다. */\n")
        f.write("window.INCOMING_BATTERIES = ")
        json.dump(rows, f, ensure_ascii=False, separators=(",", ":"))
        f.write(";\n")


def main():
    rng = random.Random(SEED)
    rows = [make_battery(i, rng) for i in range(1, COUNT + 1)]

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    js_path = os.path.join(BASE_DIR, "assets", "incoming_data.js")
    os.makedirs(os.path.dirname(js_path), exist_ok=True)
    write_js(rows, js_path)

    print(f"생성 완료: {OUT_PATH}")
    print(f"          {js_path}")
    print(f"  총 {len(rows)}대")
    print(f"  SOH 범위 {min(r['soh_percent'] for r in rows):.1f}% "
          f"~ {max(r['soh_percent'] for r in rows):.1f}%")


if __name__ == "__main__":
    main()
