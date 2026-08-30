#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EV Battery Residual Value Analyzer
사용 후 전기차 배터리 상태/재사용 적합성 평가 프로그램

실행:
    py main.py          (Windows)
    python3 main.py      (macOS / Linux)

주의:
    본 프로그램의 평가 기준(점수 배점, 등급 구간)은 실제 특정 기업의
    내부 판정 기준이 아니라, 이 프로젝트를 위해 자체적으로 설계한
    평가 모델입니다. (자세한 내용은 docs/evaluation_method.md 참고)
"""

import csv
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import batch      # noqa: E402
import routing    # noqa: E402

# ------------------------------------------------------------------
# 경로 설정
# ------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
DATA_FILE = os.path.join(DATA_DIR, "battery_data.csv")
REPORT_CSV = os.path.join(OUTPUT_DIR, "battery_report.csv")

FIELDNAMES = [
    "battery_id",
    "vehicle",
    "usage_years",
    "mileage_km",
    "soh_percent",
    "avg_temp_c",
    "max_temp_c",
    "cell_v_max",
    "cell_v_min",
    "bms_error_count",
    "fast_charge_ratio_percent",
    "registered_at",
]

REPORT_FIELDNAMES = FIELDNAMES + [
    "score_soh",
    "score_voltage",
    "score_temperature",
    "score_bms",
    "score_usage",
    "total_score",
    "grade",
    "reuse_potential",
    "risk_level",
    "evaluated_at",
]


# ------------------------------------------------------------------
# 데이터 입출력
# ------------------------------------------------------------------
def ensure_dirs():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def load_batteries():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return [row for row in reader]


def save_batteries(batteries):
    ensure_dirs()
    with open(DATA_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for row in batteries:
            writer.writerow(row)


def append_report_row(row):
    ensure_dirs()
    file_exists = os.path.exists(REPORT_CSV)
    with open(REPORT_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=REPORT_FIELDNAMES)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


# ------------------------------------------------------------------
# 입력 헬퍼
# ------------------------------------------------------------------
def ask_float(prompt, min_v=None, max_v=None):
    while True:
        raw = input(prompt).strip()
        try:
            value = float(raw)
        except ValueError:
            print("  ! 숫자로 입력해주세요.")
            continue
        if min_v is not None and value < min_v:
            print(f"  ! {min_v} 이상 값을 입력해주세요.")
            continue
        if max_v is not None and value > max_v:
            print(f"  ! {max_v} 이하 값을 입력해주세요.")
            continue
        return value


def ask_int(prompt, min_v=None, max_v=None):
    while True:
        raw = input(prompt).strip()
        try:
            value = int(raw)
        except ValueError:
            print("  ! 정수로 입력해주세요.")
            continue
        if min_v is not None and value < min_v:
            print(f"  ! {min_v} 이상 값을 입력해주세요.")
            continue
        if max_v is not None and value > max_v:
            print(f"  ! {max_v} 이하 값을 입력해주세요.")
            continue
        return value


def ask_str(prompt, default=None):
    raw = input(prompt).strip()
    if not raw and default is not None:
        return default
    return raw


# ------------------------------------------------------------------
# 평가 엔진 (배점: SOH 40 / 전압편차 20 / 온도 15 / BMS오류 15 / 사용이력 10)
# ------------------------------------------------------------------
def score_soh(soh_percent):
    soh_percent = max(0.0, min(100.0, soh_percent))
    score = soh_percent / 100.0 * 40.0
    if soh_percent >= 90:
        label = "매우 양호"
    elif soh_percent >= 80:
        label = "양호"
    elif soh_percent >= 70:
        label = "보통"
    elif soh_percent >= 60:
        label = "미흡"
    else:
        label = "심각"
    return round(score, 2), label


def score_voltage_deviation(v_max, v_min):
    deviation_mv = round((v_max - v_min) * 1000, 1)
    if deviation_mv <= 30:
        return 20.0, "매우 양호", deviation_mv
    elif deviation_mv <= 50:
        return 16.0, "양호", deviation_mv
    elif deviation_mv <= 80:
        return 10.0, "주의", deviation_mv
    elif deviation_mv <= 120:
        return 5.0, "경고", deviation_mv
    else:
        return 0.0, "심각", deviation_mv


def score_temperature(avg_temp, max_temp):
    if avg_temp <= 35 and max_temp <= 45:
        return 15.0, "정상"
    elif avg_temp <= 40 and max_temp <= 55:
        return 10.0, "주의"
    elif avg_temp <= 45 and max_temp <= 65:
        return 5.0, "경고"
    else:
        return 0.0, "심각"


def score_bms_error(error_count):
    if error_count == 0:
        return 15.0, "정상"
    elif error_count <= 2:
        return 10.0, "주의"
    elif error_count <= 5:
        return 5.0, "경고"
    else:
        return 0.0, "심각"


def score_usage(usage_years, mileage_km, fast_charge_ratio):
    # 기준: 일반적인 EV 배터리 보증 기준(8년/160,000km)을 사용률 100%로 가정
    age_ratio = min(usage_years / 8.0, 1.5)
    mileage_ratio = min(mileage_km / 160000.0, 1.5)
    usage_ratio = max(age_ratio, mileage_ratio)
    base_score = max(0.0, (1 - usage_ratio)) * 10.0

    penalty = 0.0
    if fast_charge_ratio > 60:
        penalty = 2.0
    elif fast_charge_ratio > 40:
        penalty = 1.0

    score = max(0.0, base_score - penalty)
    return round(score, 2)


def grade_from_total(total_score):
    if total_score >= 90:
        return "재사용 적합", "매우 높음", "매우 낮음", "매우 양호"
    elif total_score >= 75:
        return "양호", "높음", "낮음", "양호"
    elif total_score >= 60:
        return "추가 진단 필요", "보통", "보통", "보통"
    elif total_score >= 40:
        return "정밀 검사 필요", "낮음", "높음", "미흡"
    else:
        return "재사용 부적합", "매우 낮음", "매우 높음", "심각"


def evaluate(battery):
    soh = float(battery["soh_percent"])
    v_max = float(battery["cell_v_max"])
    v_min = float(battery["cell_v_min"])
    avg_temp = float(battery["avg_temp_c"])
    max_temp = float(battery["max_temp_c"])
    bms_errors = int(float(battery["bms_error_count"]))
    usage_years = float(battery["usage_years"])
    mileage_km = float(battery["mileage_km"])
    fast_charge_ratio = float(battery["fast_charge_ratio_percent"])

    s_soh, soh_label = score_soh(soh)
    s_volt, volt_label, deviation_mv = score_voltage_deviation(v_max, v_min)
    s_temp, temp_label = score_temperature(avg_temp, max_temp)
    s_bms, bms_label = score_bms_error(bms_errors)
    s_usage = score_usage(usage_years, mileage_km, fast_charge_ratio)

    total = round(s_soh + s_volt + s_temp + s_bms + s_usage, 2)
    grade, reuse_potential, risk_level, condition = grade_from_total(total)

    return {
        "soh": soh,
        "soh_label": soh_label,
        "v_max": v_max,
        "v_min": v_min,
        "deviation_mv": deviation_mv,
        "volt_label": volt_label,
        "avg_temp": avg_temp,
        "max_temp": max_temp,
        "temp_label": temp_label,
        "bms_errors": bms_errors,
        "bms_label": bms_label,
        "score_soh": s_soh,
        "score_voltage": s_volt,
        "score_temperature": s_temp,
        "score_bms": s_bms,
        "score_usage": s_usage,
        "total_score": total,
        "grade": grade,
        "reuse_potential": reuse_potential,
        "risk_level": risk_level,
        "condition": condition,
    }


# ------------------------------------------------------------------
# 리포트 출력
# ------------------------------------------------------------------
import unicodedata


def disp_width(text):
    """한글처럼 화면에서 두 칸을 차지하는 글자를 감안한 표시 너비."""
    return sum(2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1 for ch in text)


def pad(text, width):
    """표시 너비 기준으로 오른쪽을 공백으로 채움 (한글 정렬용)."""
    text = str(text)
    return text + " " * max(0, width - disp_width(text))


def make_bar(percent, width=20):
    percent = max(0.0, min(100.0, percent))
    filled = int(round(width * percent / 100.0))
    return "\u2588" * filled + "\u2591" * (width - filled)


def format_report(battery, result):
    L = 44          # 가로 구분선 길이
    K = 20          # 항목명 열 너비
    lines = []

    lines.append("=" * L)
    lines.append("           배터리 건강 진단서")
    lines.append("=" * L)
    lines.append(pad("배터리 ID", K) + str(battery["battery_id"]))
    lines.append(pad("차량명", K) + str(battery["vehicle"]))
    lines.append(pad("사용 이력", K) +
                 f"{battery['usage_years']}년 / {battery['mileage_km']}km")
    lines.append("-" * L)
    lines.append(pad("SOH", K) + f"{result['soh']}%")
    lines.append(pad("배터리 건강도", K) + result["soh_label"])
    lines.append("셀 전압")
    lines.append(pad("  최대", K) + f"{result['v_max']} V")
    lines.append(pad("  최소", K) + f"{result['v_min']} V")
    lines.append(pad("  편차", K) + f"{result['deviation_mv']} mV ({result['volt_label']})")
    lines.append(pad("온도", K) +
                 f"{result['temp_label']} (평균 {result['avg_temp']}C / 최고 {result['max_temp']}C)")
    lines.append(pad("BMS 오류", K) + f"{result['bms_label']} ({result['bms_errors']}회)")

    lines.append("-" * L)
    lines.append("항목별 점수 (100점 만점)")
    lines.append("-" * L)
    lines.append(pad("SOH", K) + f"{result['score_soh']:>6.2f} / 40")
    lines.append(pad("셀 전압 편차", K) + f"{result['score_voltage']:>6.2f} / 20")
    lines.append(pad("온도 이력", K) + f"{result['score_temperature']:>6.2f} / 15")
    lines.append(pad("BMS 오류", K) + f"{result['score_bms']:>6.2f} / 15")
    lines.append(pad("사용 이력", K) + f"{result['score_usage']:>6.2f} / 10")
    lines.append("-" * L)
    lines.append(pad("종합 점수", K) + f"{result['total_score']:>6.2f} / 100")

    lines.append("-" * L)
    lines.append("재사용 평가")
    lines.append("-" * L)
    lines.append(pad("배터리 상태", K) + result["condition"])
    lines.append(pad("판정 등급", K) + result["grade"])
    lines.append(pad("재사용 가능성", K) + result["reuse_potential"])
    lines.append(pad("위험도", K) + result["risk_level"])
    lines.append("")
    lines.append("잔존 성능")
    lines.append(f"{make_bar(result['soh'])} {result['soh']}%")
    lines.append("=" * L)
    lines.append("* 본 평가 기준은 실제 기업의 공식 판정 기준이 아니라")
    lines.append("  이 프로젝트를 위해 자체 설계한 모델입니다.")
    lines.append("=" * L)
    return "\n".join(lines)


# ------------------------------------------------------------------
# 메뉴 동작
# ------------------------------------------------------------------
def menu_input_battery(batteries):
    print("\n[1] 배터리 정보 입력")
    print("-" * 42)
    existing_ids = {b["battery_id"] for b in batteries}
    while True:
        battery_id = ask_str("배터리 ID (예: EV-A-001): ")
        if not battery_id:
            print("  ! ID를 입력해주세요.")
            continue
        if battery_id in existing_ids:
            print("  ! 이미 존재하는 ID입니다. 다른 ID를 입력해주세요.")
            continue
        break

    vehicle = ask_str("차량명 (예: EV A): ")
    usage_years = ask_float("사용기간 (년): ", min_v=0)
    mileage_km = ask_float("누적 주행거리 (km): ", min_v=0)
    soh_percent = ask_float("현재 SOH (%): ", min_v=0, max_v=100)
    avg_temp_c = ask_float("평균 온도 (C): ")
    max_temp_c = ask_float("최고 온도 (C): ")
    cell_v_max = ask_float("셀 최대 전압 (V): ", min_v=0)
    cell_v_min = ask_float("셀 최소 전압 (V): ", min_v=0)
    bms_error_count = ask_int("BMS 오류 발생 횟수: ", min_v=0)
    fast_charge_ratio = ask_float("급속충전 비율 (%): ", min_v=0, max_v=100)

    record = {
        "battery_id": battery_id,
        "vehicle": vehicle,
        "usage_years": usage_years,
        "mileage_km": mileage_km,
        "soh_percent": soh_percent,
        "avg_temp_c": avg_temp_c,
        "max_temp_c": max_temp_c,
        "cell_v_max": cell_v_max,
        "cell_v_min": cell_v_min,
        "bms_error_count": bms_error_count,
        "fast_charge_ratio_percent": fast_charge_ratio,
        "registered_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    batteries.append(record)
    save_batteries(batteries)
    print(f"\n✔ 배터리 '{battery_id}' 정보가 저장되었습니다. (data/battery_data.csv)")


def pick_battery(batteries):
    if not batteries:
        print("\n! 등록된 배터리 데이터가 없습니다. 먼저 [1] 배터리 정보 입력을 진행해주세요.")
        return None
    print("\n등록된 배터리 목록:")
    for i, b in enumerate(batteries, start=1):
        print(f"  {i}. {b['battery_id']}  ({b['vehicle']}, SOH {b['soh_percent']}%)")
    raw = input("분석할 배터리 번호를 선택하세요: ").strip()
    try:
        idx = int(raw) - 1
        if idx < 0 or idx >= len(batteries):
            raise ValueError
    except ValueError:
        print("  ! 올바른 번호를 입력해주세요.")
        return None
    return batteries[idx]


def menu_analyze(batteries):
    print("\n[2] 배터리 상태 분석")
    print("-" * 42)
    battery = pick_battery(batteries)
    if battery is None:
        return None, None
    result = evaluate(battery)
    print()
    print(format_report(battery, result))
    return battery, result


def menu_generate_report(batteries, last_battery, last_result):
    print("\n[3] 보고서 생성")
    print("-" * 42)
    battery, result = last_battery, last_result
    if battery is None or result is None:
        battery = pick_battery(batteries)
        if battery is None:
            return
        result = evaluate(battery)

    row = dict(battery)
    row.update(
        {
            "score_soh": result["score_soh"],
            "score_voltage": result["score_voltage"],
            "score_temperature": result["score_temperature"],
            "score_bms": result["score_bms"],
            "score_usage": result["score_usage"],
            "total_score": result["total_score"],
            "grade": result["grade"],
            "reuse_potential": result["reuse_potential"],
            "risk_level": result["risk_level"],
            "evaluated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
    )
    append_report_row(row)

    txt_path = os.path.join(OUTPUT_DIR, f"report_{battery['battery_id']}.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(format_report(battery, result))

    print(f"\n✔ 보고서가 저장되었습니다.")
    print(f"   - 요약(CSV): output/battery_report.csv")
    print(f"   - 상세(TXT): output/report_{battery['battery_id']}.txt")


def menu_route(batteries):
    """단일 배터리의 자원순환 경로(재제조/재사용/재활용)를 판정합니다."""
    print("\n[4] 자원순환 경로 판정")
    print("-" * 44)
    battery = pick_battery(batteries)
    if battery is None:
        return

    r = routing.decide(battery)

    print()
    print("=" * 44)
    print("        자원순환 경로 판정 결과")
    print("=" * 44)
    print(f"배터리 ID    {r['battery_id']}")
    print(f"SOH          {r['soh']}%")
    print(f"셀 전압 편차 {r['deviation_mv']}mV")
    print(f"최고 온도    {r['max_temp']}C")
    print(f"BMS 오류     {r['bms_errors']}회")
    print("-" * 44)
    print(f"안전성 게이트  {'통과' if r['safety_passed'] else '미달'}")
    print(f"판정 경로      >> {r['route']} ({r['route_description']})")
    if r["downgraded"]:
        print("               ※ 재제조 후보였으나 정밀 조건 미충족으로 강등")
    print("-" * 44)
    print("판정 사유")
    for reason in r["reasons"]:
        print(f"  - {reason}")
    print("-" * 44)
    print(f"예상 잔존가치  {r['estimated_value_krw']:,}원 "
          f"(팩 {r['capacity_kwh']}kWh 기준)")
    print("=" * 44)
    print("* 임계값과 단가는 자체 설계한 가정치입니다.")
    print("  근거는 docs/routing_policy.md 참고.")
    print("=" * 44)


def menu_batch():
    """입고 배터리 CSV를 한 번에 판정합니다."""
    print("\n[5] 입고 배터리 일괄 처리")
    print("-" * 44)
    try:
        batch.run()
    except FileNotFoundError as e:
        print(f"\n! {e}")


def print_menu():
    print("\n" + "=" * 44)
    print(" EV 배터리 잔존가치 분석기")
    print("=" * 44)
    print("[1] 배터리 정보 입력")
    print("[2] 배터리 상태 분석")
    print("[3] 보고서 생성")
    print("[4] 자원순환 경로 판정")
    print("[5] 입고 배터리 일괄 처리")
    print("[6] 종료")


def main():
    ensure_dirs()
    batteries = load_batteries()
    last_battery, last_result = None, None

    while True:
        print_menu()
        choice = input("메뉴를 선택하세요: ").strip()

        if choice == "1":
            menu_input_battery(batteries)
        elif choice == "2":
            last_battery, last_result = menu_analyze(batteries)
        elif choice == "3":
            menu_generate_report(batteries, last_battery, last_result)
        elif choice == "4":
            menu_route(batteries)
        elif choice == "5":
            menu_batch()
        elif choice == "6":
            print("\n프로그램을 종료합니다.")
            break
        else:
            print("\n! 1~6 중에서 선택해주세요.")


if __name__ == "__main__":
    main()
