#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Python 엔진(routing.py)과 웹 엔진(assets/routing.js)의 판정 결과가
완전히 일치하는지 검증합니다.

같은 로직을 두 언어로 구현했기 때문에, 한쪽만 고치면 웹과 터미널의
판정이 달라집니다. 파라미터를 바꾼 뒤에는 반드시 이 스크립트를 돌리세요.

실행:
    python3 tools/verify_engines.py      (Node.js 필요)

종료 코드
    0 = 모든 배터리에서 일치
    1 = 불일치 발견
"""

import csv
import json
import os
import subprocess
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

import routing  # noqa: E402

DATA_PATH = os.path.join(BASE_DIR, "data", "incoming_batteries.csv")
JS_PATH = os.path.join(BASE_DIR, "assets", "routing.js")

# 비교할 항목 (부동소수 오차를 피하려고 값은 문자열로 맞춰 비교)
COMPARE_KEYS = ["route", "safety_passed", "downgraded", "estimated_value_krw",
                "deviation_mv", "reason_text"]

JS_RUNNER = """
const fs = require('fs');
eval(fs.readFileSync(process.argv[2], 'utf8'));
const rows = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));
const out = rows.map(function (b) {
  const r = globalThis.BatteryRouting.decide(b);
  return {
    battery_id: r.battery_id,
    route: r.route,
    safety_passed: r.safety_passed,
    downgraded: r.downgraded,
    estimated_value_krw: r.estimated_value_krw,
    deviation_mv: r.deviation_mv,
    reason_text: r.reason_text
  };
});
process.stdout.write(JSON.stringify(out));
"""


def main():
    if not os.path.exists(DATA_PATH):
        print(f"! 입고 데이터가 없습니다: {DATA_PATH}")
        print("  먼저 python3 tools/generate_sample_data.py 를 실행하세요.")
        return 1

    with open(DATA_PATH, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    # --- Python 엔진 ---
    py_results = {}
    for row in rows:
        r = routing.decide(row)
        py_results[r["battery_id"]] = {k: r[k] for k in COMPARE_KEYS}

    # --- JS 엔진 (Node.js) ---
    tmp_rows = os.path.join(BASE_DIR, "output", "_verify_rows.json")
    tmp_js = os.path.join(BASE_DIR, "output", "_verify_runner.js")
    os.makedirs(os.path.dirname(tmp_rows), exist_ok=True)
    with open(tmp_rows, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False)
    with open(tmp_js, "w", encoding="utf-8") as f:
        f.write(JS_RUNNER)

    try:
        proc = subprocess.run(
            ["node", tmp_js, JS_PATH, tmp_rows],
            capture_output=True, text=True, check=True,
        )
    except FileNotFoundError:
        print("! Node.js가 설치되어 있지 않아 웹 엔진을 실행할 수 없습니다.")
        print("  https://nodejs.org 에서 설치한 뒤 다시 실행하세요.")
        return 1
    except subprocess.CalledProcessError as e:
        print("! 웹 엔진 실행 중 오류:")
        print(e.stderr)
        return 1
    finally:
        for p in (tmp_rows, tmp_js):
            if os.path.exists(p):
                os.remove(p)

    js_results = {r["battery_id"]: {k: r[k] for k in COMPARE_KEYS}
                  for r in json.loads(proc.stdout)}

    # --- 비교 ---
    mismatches = []
    for bid, py in py_results.items():
        js = js_results.get(bid)
        if js is None:
            mismatches.append((bid, "웹 엔진 결과 없음", "", ""))
            continue
        for key in COMPARE_KEYS:
            a, b = py[key], js[key]
            if isinstance(a, float) or isinstance(b, float):
                same = abs(float(a) - float(b)) < 1e-6
            else:
                same = a == b
            if not same:
                mismatches.append((bid, key, a, b))

    print(f"검증 대상: {len(py_results)}대 × {len(COMPARE_KEYS)}개 항목")
    if mismatches:
        print(f"\n✗ 불일치 {len(mismatches)}건")
        for bid, key, a, b in mismatches[:20]:
            print(f"  {bid}  {key}\n     Python: {a}\n     JS    : {b}")
        if len(mismatches) > 20:
            print(f"  … 외 {len(mismatches) - 20}건")
        return 1

    print("✓ 모든 항목이 일치합니다. (Python 엔진 ≡ 웹 엔진)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
