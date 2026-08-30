#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
입고 배터리 일괄 경로 판정

data/incoming_batteries.csv 를 읽어 배터리 한 대씩 자원순환 경로를 판정하고,
경로별 집계를 화면에 출력한 뒤 결과를 CSV로 저장합니다.

실행:
    py batch.py            (Windows)
    python3 batch.py       (macOS / Linux)
"""

import csv
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import routing  # noqa: E402

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IN_PATH = os.path.join(BASE_DIR, "data", "incoming_batteries.csv")
OUT_DIR = os.path.join(BASE_DIR, "output")
OUT_CSV = os.path.join(OUT_DIR, "routing_result.csv")

OUT_FIELDS = [
    "battery_id", "vehicle", "capacity_kwh", "usage_years", "mileage_km",
    "soh", "deviation_mv", "avg_temp", "max_temp", "bms_errors",
    "fast_charge_ratio", "route", "route_description", "safety_passed",
    "downgraded", "estimated_value_krw", "reason_text",
]


def disp_width(text):
    import unicodedata
    return sum(2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
               for ch in str(text))


def pad(text, width):
    text = str(text)
    return text + " " * max(0, width - disp_width(text))


def rpad(text, width):
    text = str(text)
    return " " * max(0, width - disp_width(text)) + text


def load_batteries(path=IN_PATH):
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"입고 데이터가 없습니다: {path}\n"
            f"먼저 `python3 tools/generate_sample_data.py` 를 실행하세요."
        )
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def bar(count, total, width=24):
    if not total:
        return "░" * width
    filled = int(round(width * count / total))
    return "█" * filled + "░" * (width - filled)


def print_report(results, summary):
    L = 60
    print()
    print("=" * L)
    print("        사용 후 배터리 자원순환 경로 판정 결과")
    print("=" * L)
    print(pad("입고 총량", 22) + f"{summary['total']}대")
    print(pad("안전성 미달", 22) + f"{summary['safety_failed']}대")
    print(pad("재제조 → 재사용 강등", 22) + f"{summary['downgraded']}대")
    print("-" * L)
    print("경로별 분류")
    print("-" * L)

    for route in routing.ROUTES:
        b = summary["routes"][route]
        print(pad(route, 8) + bar(b["count"], summary["total"]) +
              rpad(f"{b['count']}대", 7) + rpad(f"{b['share']}%", 8))
        print(pad("", 8) + f"{routing.ROUTE_DESCRIPTION[route]} · "
              f"평균 SOH {b['avg_soh']}% · 추정가치 {b['value']:,}원")
        print()

    print("-" * L)
    print("안전성 미달 사유")
    print("-" * L)
    if summary["safety_reason_counts"]:
        for reason, count in sorted(summary["safety_reason_counts"].items(),
                                    key=lambda x: -x[1]):
            print(pad("  " + reason, 22) + f"{count}건")
    else:
        print("  없음")

    # 이 시스템의 핵심 사례: SOH는 높지만 안전성 때문에 탈락한 배터리
    overridden = [r for r in results
                  if not r["safety_passed"]
                  and r["soh"] >= routing.SOH_THRESHOLDS["remanufacture"]]
    print("-" * L)
    print("주목: SOH 기준은 넘었지만 안전성으로 탈락한 배터리")
    print("-" * L)
    if overridden:
        for r in overridden[:5]:
            print(f"  {r['battery_id']}  SOH {r['soh']:.1f}%  →  재활용")
            print(f"      사유: {'; '.join(r['safety_reasons'])}")
        if len(overridden) > 5:
            print(f"  … 외 {len(overridden) - 5}대")
        print()
        print(f"  총 {len(overridden)}대. SOH만으로 판단했다면 전기차에 재투입됐을 배터리입니다.")
    else:
        print("  해당 없음")

    print("-" * L)
    print(pad("총 추정 잔존가치", 22) + f"{summary['total_value']:,}원")
    print("=" * L)
    print("* 단가는 가정치이며 실제 거래가가 아닙니다. 근거와 한계는")
    print("  docs/routing_policy.md 를 참고하세요.")
    print("=" * L)


def save_csv(results, path=OUT_CSV):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=OUT_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for r in results:
            writer.writerow(r)
    return path


def run(path=IN_PATH, save=True, quiet=False):
    batteries = load_batteries(path)
    results = [routing.decide(b) for b in batteries]
    summary = routing.summarize(results)

    if not quiet:
        print_report(results, summary)

    if save:
        out = save_csv(results)
        if not quiet:
            print(f"\n결과 저장: {os.path.relpath(out, BASE_DIR)}")
            print(f"판정 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    return results, summary


if __name__ == "__main__":
    run()
