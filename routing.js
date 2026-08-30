/* ==========================================================================
   사용 후 배터리 자원순환 경로 판정 엔진 (웹)

   routing.py 와 동일한 판정 로직입니다. 파라미터를 바꿀 때는
   양쪽을 함께 수정해야 하며, 두 엔진의 결과가 일치하는지는
   tools/verify_engines.py 로 검증합니다.
   ========================================================================== */
(function (global) {
  "use strict";

  // --- 1단계: 안전성 게이트 ---------------------------------------
  var SAFETY_LIMITS = {
    cell_deviation_mv: 100.0,
    max_temp_c: 60.0,
    bms_error_count: 5
  };

  // --- 2단계: SOH 1차 분류 ----------------------------------------
  // 재제조 80% 기준은 포엔 관련 보도(전자신문 2024-08-22) 참고
  var SOH_THRESHOLDS = {
    remanufacture: 80.0,
    reuse: 60.0
  };

  // --- 3단계: 재제조 정밀 조건 ------------------------------------
  var REMANUFACTURE_LIMITS = {
    cell_deviation_mv: 50.0,
    max_temp_c: 50.0,
    bms_error_count: 0,
    fast_charge_ratio_percent: 60.0
  };

  // --- 4단계: 경제성 추정 단가 (가정치) ---------------------------
  var VALUE_ASSUMPTIONS_KRW_PER_KWH = {
    "재제조": 60000,
    "재사용": 25000,
    "재활용": 8000
  };

  var DEFAULT_PACK_CAPACITY_KWH = 60.0;
  var ROUTES = ["재제조", "재사용", "재활용"];
  var ROUTE_DESCRIPTION = {
    "재제조": "전기차 배터리로 재투입",
    "재사용": "ESS 등으로 용도 전환",
    "재활용": "분해 후 원료 추출"
  };

  function toNum(v, dflt) {
    var n = parseFloat(v);
    return isFinite(n) ? n : (dflt === undefined ? 0 : dflt);
  }

  function round1(n) { return Math.round(n * 10) / 10; }

  function normalize(b) {
    var vMax = toNum(b.cell_v_max);
    var vMin = toNum(b.cell_v_min);
    var cap = toNum(b.pack_capacity_kwh, DEFAULT_PACK_CAPACITY_KWH) || DEFAULT_PACK_CAPACITY_KWH;
    return {
      battery_id: b.battery_id === undefined ? "-" : b.battery_id,
      vehicle: b.vehicle === undefined ? "-" : b.vehicle,
      capacity_kwh: cap,
      usage_years: toNum(b.usage_years),
      mileage_km: toNum(b.mileage_km),
      soh: toNum(b.soh_percent),
      avg_temp: toNum(b.avg_temp_c),
      max_temp: toNum(b.max_temp_c),
      v_max: vMax,
      v_min: vMin,
      deviation_mv: round1((vMax - vMin) * 1000),
      bms_errors: Math.trunc(toNum(b.bms_error_count)),
      fast_charge_ratio: toNum(b.fast_charge_ratio_percent)
    };
  }

  function safetyCheck(b) {
    var reasons = [];
    if (b.deviation_mv > SAFETY_LIMITS.cell_deviation_mv) {
      reasons.push(["셀 전압 편차 초과",
        "셀 전압 편차 " + Math.round(b.deviation_mv) + "mV (한계 " +
        Math.round(SAFETY_LIMITS.cell_deviation_mv) + "mV 초과)"]);
    }
    if (b.max_temp > SAFETY_LIMITS.max_temp_c) {
      reasons.push(["온도 이력 초과",
        "최고 온도 " + Math.round(b.max_temp) + "℃ (한계 " +
        Math.round(SAFETY_LIMITS.max_temp_c) + "℃ 초과)"]);
    }
    if (b.bms_errors > SAFETY_LIMITS.bms_error_count) {
      reasons.push(["BMS 오류 과다",
        "BMS 오류 " + b.bms_errors + "회 (허용 " +
        SAFETY_LIMITS.bms_error_count + "회 초과)"]);
    }
    return { passed: reasons.length === 0, reasons: reasons };
  }

  function remanufactureCheck(b) {
    var reasons = [];
    if (b.deviation_mv > REMANUFACTURE_LIMITS.cell_deviation_mv) {
      reasons.push("셀 전압 편차 " + Math.round(b.deviation_mv) + "mV (재제조 기준 " +
        Math.round(REMANUFACTURE_LIMITS.cell_deviation_mv) + "mV 이하)");
    }
    if (b.max_temp > REMANUFACTURE_LIMITS.max_temp_c) {
      reasons.push("최고 온도 " + Math.round(b.max_temp) + "℃ (재제조 기준 " +
        Math.round(REMANUFACTURE_LIMITS.max_temp_c) + "℃ 이하)");
    }
    if (b.bms_errors > REMANUFACTURE_LIMITS.bms_error_count) {
      reasons.push("BMS 오류 " + b.bms_errors + "회 (재제조 기준 0회)");
    }
    if (b.fast_charge_ratio > REMANUFACTURE_LIMITS.fast_charge_ratio_percent) {
      reasons.push("급속충전 비율 " + Math.round(b.fast_charge_ratio) + "% (재제조 기준 " +
        Math.round(REMANUFACTURE_LIMITS.fast_charge_ratio_percent) + "% 이하)");
    }
    return { passed: reasons.length === 0, reasons: reasons };
  }

  function estimateValue(route, capacityKwh, soh) {
    var unit = VALUE_ASSUMPTIONS_KRW_PER_KWH[route];
    if (route === "재활용") return Math.round(capacityKwh * unit);
    return Math.round(capacityKwh * (soh / 100) * unit);
  }

  function decide(battery) {
    var b = normalize(battery);
    var safety = safetyCheck(b);
    var downgraded = false;
    var route, reasons;

    var safetyMessages = safety.reasons.map(function (r) { return r[1]; });
    var safetyCategories = safety.reasons.map(function (r) { return r[0]; });

    if (!safety.passed) {
      route = "재활용";
      reasons = ["안전성 미달"].concat(safetyMessages);
    } else if (b.soh >= SOH_THRESHOLDS.remanufacture) {
      var rc = remanufactureCheck(b);
      if (rc.passed) {
        route = "재제조";
        reasons = ["SOH " + b.soh.toFixed(1) + "% (기준 " +
                   Math.round(SOH_THRESHOLDS.remanufacture) + "% 이상)",
                   "재제조 정밀 조건 충족"];
      } else {
        route = "재사용";
        downgraded = true;
        reasons = ["SOH " + b.soh.toFixed(1) + "%로 재제조 후보였으나 정밀 조건 미충족"]
                    .concat(rc.reasons);
      }
    } else if (b.soh >= SOH_THRESHOLDS.reuse) {
      route = "재사용";
      reasons = ["SOH " + b.soh.toFixed(1) + "% (" +
                 Math.round(SOH_THRESHOLDS.reuse) + "~" +
                 Math.round(SOH_THRESHOLDS.remanufacture) + "% 구간)"];
    } else {
      route = "재활용";
      reasons = ["SOH " + b.soh.toFixed(1) + "% (기준 " +
                 Math.round(SOH_THRESHOLDS.reuse) + "% 미만)"];
    }

    var out = {};
    for (var k in b) { if (b.hasOwnProperty(k)) out[k] = b[k]; }
    out.route = route;
    out.route_description = ROUTE_DESCRIPTION[route];
    out.reasons = reasons;
    out.reason_text = reasons.join(" / ");
    out.safety_passed = safety.passed;
    out.safety_reasons = safetyMessages;
    out.safety_categories = safetyCategories;
    out.downgraded = downgraded;
    out.estimated_value_krw = estimateValue(route, b.capacity_kwh, b.soh);
    return out;
  }

  function summarize(results) {
    var total = results.length;
    var summary = {
      total: total, routes: {}, safety_failed: 0, downgraded: 0,
      total_value: 0, safety_reason_counts: {}
    };
    ROUTES.forEach(function (r) {
      summary.routes[r] = { count: 0, value: 0, soh_sum: 0 };
    });

    results.forEach(function (r) {
      var bucket = summary.routes[r.route];
      bucket.count += 1;
      bucket.value += r.estimated_value_krw;
      bucket.soh_sum += r.soh;
      summary.total_value += r.estimated_value_krw;
      if (!r.safety_passed) {
        summary.safety_failed += 1;
        r.safety_categories.forEach(function (c) {
          summary.safety_reason_counts[c] = (summary.safety_reason_counts[c] || 0) + 1;
        });
      }
      if (r.downgraded) summary.downgraded += 1;
    });

    ROUTES.forEach(function (r) {
      var b = summary.routes[r];
      b.share = total ? Math.round(b.count / total * 1000) / 10 : 0;
      b.avg_soh = b.count ? Math.round(b.soh_sum / b.count * 10) / 10 : 0;
    });
    return summary;
  }

  global.BatteryRouting = {
    ROUTES: ROUTES,
    ROUTE_DESCRIPTION: ROUTE_DESCRIPTION,
    SOH_THRESHOLDS: SOH_THRESHOLDS,
    SAFETY_LIMITS: SAFETY_LIMITS,
    REMANUFACTURE_LIMITS: REMANUFACTURE_LIMITS,
    VALUE_ASSUMPTIONS_KRW_PER_KWH: VALUE_ASSUMPTIONS_KRW_PER_KWH,
    decide: decide,
    summarize: summarize
  };
})(typeof window !== "undefined" ? window : globalThis);
