#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
사용 후 배터리 자원순환 경로 판정 엔진
Battery End-of-Life Routing Engine

사용 후 전기차 배터리를 세 갈래 중 하나로 보내는 판정을 수행합니다.

    재제조 (Remanufacture)  : 전기차 배터리로 재투입
    재사용 (Reuse / ESS)    : 에너지저장장치 등으로 용도 전환
    재활용 (Recycle)        : 분해 후 원료 추출

판정 순서
    1) 안전성 게이트  — 하나라도 걸리면 SOH와 무관하게 '재활용'
    2) SOH 1차 분류   — 80% 이상 / 60~80% / 60% 미만
    3) 재제조 정밀조건 — 전기차에 다시 들어가므로 더 엄격하게 재검
    4) 경제성 추정    — 경로별 예상 잔존가치

주의
    본 모듈의 임계값과 단가는 특정 기업의 내부 판정 기준이 아닙니다.
    공개된 보도자료·산업 자료를 참고해 이 프로젝트를 위해 설계한 모델이며,
    근거와 한계는 docs/routing_policy.md 에 정리했습니다.
"""

# ==================================================================
# 판정 파라미터 — 정책을 바꾸려면 이 블록만 수정하면 됩니다
# ==================================================================

# --- 1단계: 안전성 게이트 ---------------------------------------
# 하나라도 초과하면 잔존 성능과 무관하게 재활용으로 보냅니다.
# 재제조·재사용은 배터리를 계속 '쓰는' 경로이므로 안전이 선행 조건입니다.
SAFETY_LIMITS = {
    "cell_deviation_mv": 100.0,   # 셀 전압 편차 상한
    "max_temp_c": 60.0,           # 최고 온도 이력 상한
    "bms_error_count": 5,         # BMS 오류 누적 허용 횟수
}

# --- 2단계: SOH 1차 분류 -----------------------------------------
# 재제조 기준 80%는 포엔 관련 보도(전자신문, 2024-08-22)에서
# "잔존 수명 80% 이상 선별"로 언급된 수치를 참고했습니다.
SOH_THRESHOLDS = {
    "remanufacture": 80.0,        # 이상이면 재제조 후보
    "reuse": 60.0,                # 이상이면 재사용(ESS) 후보
}

# --- 3단계: 재제조 정밀 조건 -------------------------------------
# 다시 전기차에 들어가는 만큼 안전성 게이트보다 엄격하게 재검합니다.
# 미충족 시 재사용(ESS)으로 강등합니다.
REMANUFACTURE_LIMITS = {
    "cell_deviation_mv": 50.0,
    "max_temp_c": 50.0,
    "bms_error_count": 0,
    "fast_charge_ratio_percent": 60.0,
}

# --- 4단계: 경제성 추정 단가 (가정치) ----------------------------
# ⚠️ 아래 단가는 공개된 확정 시세가 아니라 이 프로젝트의 '가정치'입니다.
#    상대적 크기 비교(재제조 > 재사용 > 재활용)를 보여주기 위한 값이며,
#    실제 거래가와 다릅니다. 실 데이터가 확보되면 이 값만 교체하면 됩니다.
VALUE_ASSUMPTIONS_KRW_PER_KWH = {
    "재제조": 60000,
    "재사용": 25000,
    "재활용": 8000,
}

DEFAULT_PACK_CAPACITY_KWH = 60.0   # 용량 정보가 없을 때 가정하는 팩 용량

ROUTES = ("재제조", "재사용", "재활용")

ROUTE_DESCRIPTION = {
    "재제조": "전기차 배터리로 재투입",
    "재사용": "ESS 등으로 용도 전환",
    "재활용": "분해 후 원료 추출",
}


# ==================================================================
# 입력 정규화
# ==================================================================
def _to_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def normalize(battery):
    """CSV 문자열이든 숫자든 동일한 형태로 정리합니다."""
    v_max = _to_float(battery.get("cell_v_max"))
    v_min = _to_float(battery.get("cell_v_min"))
    return {
        "battery_id": battery.get("battery_id", "-"),
        "vehicle": battery.get("vehicle", "-"),
        "capacity_kwh": _to_float(battery.get("pack_capacity_kwh"), DEFAULT_PACK_CAPACITY_KWH)
                        or DEFAULT_PACK_CAPACITY_KWH,
        "usage_years": _to_float(battery.get("usage_years")),
        "mileage_km": _to_float(battery.get("mileage_km")),
        "soh": _to_float(battery.get("soh_percent")),
        "avg_temp": _to_float(battery.get("avg_temp_c")),
        "max_temp": _to_float(battery.get("max_temp_c")),
        "v_max": v_max,
        "v_min": v_min,
        "deviation_mv": round((v_max - v_min) * 1000, 1),
        "bms_errors": int(_to_float(battery.get("bms_error_count"))),
        "fast_charge_ratio": _to_float(battery.get("fast_charge_ratio_percent")),
    }


# ==================================================================
# 1단계 — 안전성 게이트
# ==================================================================
def safety_check(b):
    """
    반환: (통과여부, 위반사유 리스트)
    사유를 문자열로 남겨야 '왜 이 판정이 나왔는지' 설명할 수 있습니다.
    """
    reasons = []
    if b["deviation_mv"] > SAFETY_LIMITS["cell_deviation_mv"]:
        reasons.append((
            "셀 전압 편차 초과",
            f"셀 전압 편차 {b['deviation_mv']:.0f}mV "
            f"(한계 {SAFETY_LIMITS['cell_deviation_mv']:.0f}mV 초과)"
        ))
    if b["max_temp"] > SAFETY_LIMITS["max_temp_c"]:
        reasons.append((
            "온도 이력 초과",
            f"최고 온도 {b['max_temp']:.0f}℃ "
            f"(한계 {SAFETY_LIMITS['max_temp_c']:.0f}℃ 초과)"
        ))
    if b["bms_errors"] > SAFETY_LIMITS["bms_error_count"]:
        reasons.append((
            "BMS 오류 과다",
            f"BMS 오류 {b['bms_errors']}회 "
            f"(허용 {SAFETY_LIMITS['bms_error_count']}회 초과)"
        ))
    return (len(reasons) == 0), reasons


# ==================================================================
# 3단계 — 재제조 정밀 조건
# ==================================================================
def remanufacture_check(b):
    """재제조(전기차 재투입) 가능 여부와 미충족 사유."""
    reasons = []
    if b["deviation_mv"] > REMANUFACTURE_LIMITS["cell_deviation_mv"]:
        reasons.append(
            f"셀 전압 편차 {b['deviation_mv']:.0f}mV "
            f"(재제조 기준 {REMANUFACTURE_LIMITS['cell_deviation_mv']:.0f}mV 이하)"
        )
    if b["max_temp"] > REMANUFACTURE_LIMITS["max_temp_c"]:
        reasons.append(
            f"최고 온도 {b['max_temp']:.0f}℃ "
            f"(재제조 기준 {REMANUFACTURE_LIMITS['max_temp_c']:.0f}℃ 이하)"
        )
    if b["bms_errors"] > REMANUFACTURE_LIMITS["bms_error_count"]:
        reasons.append(f"BMS 오류 {b['bms_errors']}회 (재제조 기준 0회)")
    if b["fast_charge_ratio"] > REMANUFACTURE_LIMITS["fast_charge_ratio_percent"]:
        reasons.append(
            f"급속충전 비율 {b['fast_charge_ratio']:.0f}% "
            f"(재제조 기준 {REMANUFACTURE_LIMITS['fast_charge_ratio_percent']:.0f}% 이하)"
        )
    return (len(reasons) == 0), reasons


# ==================================================================
# 4단계 — 경제성 추정
# ==================================================================
def estimate_value(route, capacity_kwh, soh):
    """
    경로별 예상 잔존가치(원). 단가는 가정치입니다.

    재제조·재사용은 '남아 있는 용량'을 쓰는 것이므로 SOH를 곱하고,
    재활용은 원료를 회수하는 것이라 잔존 용량과 무관하게 팩 용량 기준으로 봅니다.
    """
    unit = VALUE_ASSUMPTIONS_KRW_PER_KWH[route]
    if route == "재활용":
        return int(round(capacity_kwh * unit))
    usable_kwh = capacity_kwh * (soh / 100.0)
    return int(round(usable_kwh * unit))


# ==================================================================
# 통합 판정
# ==================================================================
def decide(battery):
    """
    배터리 한 대의 자원순환 경로를 판정합니다.

    반환 딕셔너리의 핵심 키
        route          : 재제조 / 재사용 / 재활용
        reasons        : 그 경로로 간 이유(사람이 읽는 문장)
        safety_passed  : 안전성 게이트 통과 여부
        downgraded     : 재제조 후보였다가 강등됐는지
        estimated_value_krw : 예상 잔존가치(원)
    """
    b = normalize(battery)

    safe, safety_reasons = safety_check(b)
    downgraded = False

    safety_messages = [msg for _, msg in safety_reasons]
    safety_categories = [cat for cat, _ in safety_reasons]

    if not safe:
        route = "재활용"
        reasons = ["안전성 미달"] + safety_messages
    elif b["soh"] >= SOH_THRESHOLDS["remanufacture"]:
        ok, reman_reasons = remanufacture_check(b)
        if ok:
            route = "재제조"
            reasons = [f"SOH {b['soh']:.1f}% (기준 {SOH_THRESHOLDS['remanufacture']:.0f}% 이상)",
                       "재제조 정밀 조건 충족"]
        else:
            route = "재사용"
            downgraded = True
            reasons = [f"SOH {b['soh']:.1f}%로 재제조 후보였으나 정밀 조건 미충족"] + reman_reasons
    elif b["soh"] >= SOH_THRESHOLDS["reuse"]:
        route = "재사용"
        reasons = [f"SOH {b['soh']:.1f}% "
                   f"({SOH_THRESHOLDS['reuse']:.0f}~{SOH_THRESHOLDS['remanufacture']:.0f}% 구간)"]
    else:
        route = "재활용"
        reasons = [f"SOH {b['soh']:.1f}% (기준 {SOH_THRESHOLDS['reuse']:.0f}% 미만)"]

    value = estimate_value(route, b["capacity_kwh"], b["soh"])

    result = dict(b)
    result.update({
        "route": route,
        "route_description": ROUTE_DESCRIPTION[route],
        "reasons": reasons,
        "reason_text": " / ".join(reasons),
        "safety_passed": safe,
        "safety_reasons": safety_messages,
        "safety_categories": safety_categories,
        "downgraded": downgraded,
        "estimated_value_krw": value,
    })
    return result


def summarize(results):
    """여러 대의 판정 결과를 경로별로 집계합니다."""
    total = len(results)
    summary = {
        "total": total,
        "routes": {r: {"count": 0, "value": 0, "soh_sum": 0.0} for r in ROUTES},
        "safety_failed": 0,
        "downgraded": 0,
        "total_value": 0,
        "safety_reason_counts": {},
    }
    for r in results:
        bucket = summary["routes"][r["route"]]
        bucket["count"] += 1
        bucket["value"] += r["estimated_value_krw"]
        bucket["soh_sum"] += r["soh"]
        summary["total_value"] += r["estimated_value_krw"]
        if not r["safety_passed"]:
            summary["safety_failed"] += 1
            for cat in r["safety_categories"]:
                summary["safety_reason_counts"][cat] = \
                    summary["safety_reason_counts"].get(cat, 0) + 1
        if r["downgraded"]:
            summary["downgraded"] += 1

    for r in ROUTES:
        bucket = summary["routes"][r]
        c = bucket["count"]
        bucket["share"] = round(c / total * 100, 1) if total else 0.0
        bucket["avg_soh"] = round(bucket["soh_sum"] / c, 1) if c else 0.0
    return summary
