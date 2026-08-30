/* ==========================================================================
   EV Battery Residual Value Analyzer — 웹 평가 엔진
   main.py 의 평가 로직과 동일한 산정식을 사용합니다.
   (배점: SOH 40 / 셀 전압편차 20 / 온도 15 / BMS 오류 15 / 사용 이력 10)
   ========================================================================== */
(function () {
  "use strict";

  /* ---------------- 평가 엔진 ---------------- */

  function scoreSoh(soh) {
    const v = Math.max(0, Math.min(100, soh));
    const score = (v / 100) * 40;
    let label;
    if (v >= 90) label = "매우 양호";
    else if (v >= 80) label = "양호";
    else if (v >= 70) label = "보통";
    else if (v >= 60) label = "미흡";
    else label = "심각";
    return { score: round2(score), label };
  }

  function scoreVoltageDeviation(vMax, vMin) {
    const dev = Math.round((vMax - vMin) * 1000 * 10) / 10; // mV
    if (dev <= 30) return { score: 20, label: "매우 양호", dev };
    if (dev <= 50) return { score: 16, label: "양호", dev };
    if (dev <= 80) return { score: 10, label: "주의", dev };
    if (dev <= 120) return { score: 5, label: "경고", dev };
    return { score: 0, label: "심각", dev };
  }

  function scoreTemperature(avg, max) {
    if (avg <= 35 && max <= 45) return { score: 15, label: "정상" };
    if (avg <= 40 && max <= 55) return { score: 10, label: "주의" };
    if (avg <= 45 && max <= 65) return { score: 5, label: "경고" };
    return { score: 0, label: "심각" };
  }

  function scoreBmsError(count) {
    if (count === 0) return { score: 15, label: "정상" };
    if (count <= 2) return { score: 10, label: "주의" };
    if (count <= 5) return { score: 5, label: "경고" };
    return { score: 0, label: "심각" };
  }

  function scoreUsage(years, km, fastRatio) {
    // 보증 기준(8년 / 160,000km)을 사용률 100% 기준선으로 가정
    const ageRatio = Math.min(years / 8, 1.5);
    const mileageRatio = Math.min(km / 160000, 1.5);
    const usageRatio = Math.max(ageRatio, mileageRatio);
    const base = Math.max(0, 1 - usageRatio) * 10;

    let penalty = 0;
    if (fastRatio > 60) penalty = 2;
    else if (fastRatio > 40) penalty = 1;

    return round2(Math.max(0, base - penalty));
  }

  function gradeFromTotal(total) {
    if (total >= 90)
      return { grade: "재사용 적합", reuse: "매우 높음", risk: "매우 낮음",
               condition: "매우 양호", status: "good", icon: "●" };
    if (total >= 75)
      return { grade: "양호", reuse: "높음", risk: "낮음",
               condition: "양호", status: "good", icon: "●" };
    if (total >= 60)
      return { grade: "추가 진단 필요", reuse: "보통", risk: "보통",
               condition: "보통", status: "warning", icon: "▲" };
    if (total >= 40)
      return { grade: "정밀 검사 필요", reuse: "낮음", risk: "높음",
               condition: "미흡", status: "serious", icon: "▲" };
    return { grade: "재사용 부적합", reuse: "매우 낮음", risk: "매우 높음",
             condition: "심각", status: "critical", icon: "✕" };
  }

  function evaluate(b) {
    const soh = scoreSoh(b.soh);
    const volt = scoreVoltageDeviation(b.vMax, b.vMin);
    const temp = scoreTemperature(b.avgTemp, b.maxTemp);
    const bms = scoreBmsError(b.bmsErrors);
    const usage = scoreUsage(b.years, b.km, b.fastRatio);

    const total = round2(soh.score + volt.score + temp.score + bms.score + usage);
    const verdict = gradeFromTotal(total);

    return { soh, volt, temp, bms, usage, total, verdict };
  }

  function round2(n) { return Math.round(n * 100) / 100; }

  /* ---------------- 샘플 데이터 (data/battery_data.csv 와 동일) ---------------- */

  const PRESETS = {
    A: { battery_id: "EV-A-001", vehicle: "EV A", usage_years: 5, mileage_km: 120000,
         soh_percent: 87.4, avg_temp_c: 29, max_temp_c: 43,
         cell_v_max: 4.08, cell_v_min: 4.03, bms_error_count: 0, fast_charge_ratio_percent: 38 },
    B: { battery_id: "EV-B-002", vehicle: "EV B", usage_years: 7, mileage_km: 168000,
         soh_percent: 74.1, avg_temp_c: 31, max_temp_c: 52,
         cell_v_max: 4.11, cell_v_min: 4.02, bms_error_count: 3, fast_charge_ratio_percent: 55 },
    C: { battery_id: "EV-C-003", vehicle: "EV C", usage_years: 2, mileage_km: 38000,
         soh_percent: 96.2, avg_temp_c: 26, max_temp_c: 39,
         cell_v_max: 4.06, cell_v_min: 4.05, bms_error_count: 0, fast_charge_ratio_percent: 22 },
    D: { battery_id: "EV-D-004", vehicle: "EV D", usage_years: 9, mileage_km: 192000,
         soh_percent: 58.6, avg_temp_c: 34, max_temp_c: 61,
         cell_v_max: 4.15, cell_v_min: 3.94, bms_error_count: 7, fast_charge_ratio_percent: 68 }
  };

  /* ---------------- DOM ---------------- */

  const $ = (id) => document.getElementById(id);

  const FIELDS = ["battery_id", "vehicle", "usage_years", "mileage_km", "soh_percent",
                  "avg_temp_c", "max_temp_c", "cell_v_max", "cell_v_min",
                  "bms_error_count", "fast_charge_ratio_percent"];

  const SCORE_ROWS = [
    { key: "soh",   name: "SOH",                 max: 40 },
    { key: "volt",  name: "셀 전압 편차",         max: 20 },
    { key: "temp",  name: "온도 이력",            max: 15 },
    { key: "bms",   name: "BMS 오류",             max: 15 },
    { key: "usage", name: "사용 이력",            max: 10 }
  ];

  function readForm() {
    const num = (id) => parseFloat($(id).value);
    const vals = {
      id: $("battery_id").value.trim() || "—",
      years: num("usage_years"),
      km: num("mileage_km"),
      soh: num("soh_percent"),
      avgTemp: num("avg_temp_c"),
      maxTemp: num("max_temp_c"),
      vMax: num("cell_v_max"),
      vMin: num("cell_v_min"),
      bmsErrors: Math.round(num("bms_error_count")),
      fastRatio: num("fast_charge_ratio_percent")
    };

    const numeric = ["years", "km", "soh", "avgTemp", "maxTemp", "vMax", "vMin", "bmsErrors", "fastRatio"];
    for (const k of numeric) {
      if (!Number.isFinite(vals[k])) return { error: "모든 숫자 항목을 입력해주세요." };
    }
    if (vals.soh < 0 || vals.soh > 100) return { error: "SOH는 0~100% 사이여야 합니다." };
    if (vals.vMin > vals.vMax) return { error: "셀 최소 전압이 최대 전압보다 클 수 없습니다." };
    if (vals.avgTemp > vals.maxTemp) return { error: "평균 온도가 최고 온도보다 클 수 없습니다." };
    if (vals.years < 0 || vals.km < 0 || vals.bmsErrors < 0) return { error: "음수는 입력할 수 없습니다." };

    return { values: vals };
  }

  function buildScoreRows() {
    const list = $("score-list");
    list.innerHTML = "";
    SCORE_ROWS.forEach((row) => {
      const el = document.createElement("div");
      el.className = "score-row";
      el.innerHTML =
        '<div class="score-top">' +
          '<span class="score-name">' + row.name + '</span>' +
          '<span class="score-num"><span data-val="' + row.key + '">0</span>' +
          '<small> / ' + row.max + '</small></span>' +
        '</div>' +
        '<div class="meter"><div class="meter-fill" data-bar="' + row.key + '" style="width:0%"></div></div>';
      list.appendChild(el);
    });
  }

  function render() {
    const parsed = readForm();
    const errBox = $("form-error");

    if (parsed.error) {
      errBox.textContent = parsed.error;
      errBox.hidden = false;
      return;
    }
    errBox.hidden = true;

    const b = parsed.values;
    const r = evaluate(b);

    // 헤더 / 총점 / 등급
    $("r-id").textContent = b.id;
    $("r-total").textContent = r.total.toFixed(1);

    const badge = $("r-grade-badge");
    badge.setAttribute("data-status", r.verdict.status);
    $("r-grade-icon").textContent = r.verdict.icon;
    $("r-grade").textContent = r.verdict.grade;
    $("r-reuse").textContent = "재사용 가능성 " + r.verdict.reuse;
    $("r-risk").textContent = "위험도 " + r.verdict.risk;

    // SOH 미터
    $("r-soh").textContent = b.soh.toFixed(1);
    $("r-soh-bar").style.width = Math.max(0, Math.min(100, b.soh)) + "%";
    $("r-soh-label").textContent = "배터리 건강도 " + r.soh.label;

    // 항목별 점수
    const scores = {
      soh: r.soh.score, volt: r.volt.score, temp: r.temp.score,
      bms: r.bms.score, usage: r.usage
    };
    SCORE_ROWS.forEach((row) => {
      const val = scores[row.key];
      const valEl = document.querySelector('[data-val="' + row.key + '"]');
      const barEl = document.querySelector('[data-bar="' + row.key + '"]');
      if (valEl) valEl.textContent = val.toFixed(2);
      if (barEl) barEl.style.width = (val / row.max) * 100 + "%";
    });

    // 세부 판독
    $("d-volt").textContent = r.volt.dev.toFixed(1) + " mV";
    $("d-volt-s").textContent = r.volt.label;
    $("d-temp").textContent = b.avgTemp.toFixed(1) + " / " + b.maxTemp.toFixed(1) + " ℃";
    $("d-temp-s").textContent = r.temp.label;
    $("d-bms").textContent = b.bmsErrors + " 회";
    $("d-bms-s").textContent = r.bms.label;
    $("d-usage").textContent =
      b.years + "년 / " + Math.round(b.km).toLocaleString("ko-KR") + "km" +
      " · 급속 " + b.fastRatio + "%";
    $("d-usage-s").textContent = r.usage.toFixed(2) + " / 10";
  }

  function applyPreset(key, btn) {
    const p = PRESETS[key];
    if (!p) return;
    FIELDS.forEach((f) => { if ($(f) && p[f] !== undefined) $(f).value = p[f]; });
    $("soh_range").value = p.soh_percent;

    document.querySelectorAll(".chip").forEach((c) =>
      c.setAttribute("aria-pressed", String(c === btn)));
    render();
  }

  /* ---------------- 소유자 정보 / 테마 ---------------- */

  function applyOwner() {
    const o = $("owner");
    if (!o) return;
    const name = o.dataset.name;
    const gh = o.dataset.github;
    const email = o.dataset.email;
    const repoUrl = "https://github.com/" + gh + "/ev-battery-analyzer";

    ["about-name", "footer-name"].forEach((id) => { if ($(id)) $(id).textContent = name; });
    if ($("about-github")) $("about-github").href = "https://github.com/" + gh;
    if ($("about-email")) $("about-email").href = "mailto:" + email;
    if ($("repo-link")) $("repo-link").href = repoUrl;
    document.querySelectorAll(".repo-link").forEach((a) => { a.href = repoUrl; });
    if ($("year")) $("year").textContent = new Date().getFullYear();
  }

  function isDarkNow() {
    const root = document.documentElement;
    const stamped = root.getAttribute("data-theme");
    if (stamped === "dark") return true;
    if (stamped === "light") return false;
    return window.matchMedia("(prefers-color-scheme: dark)").matches;
  }

  function syncThemeIcon() {
    const icon = $("theme-icon");
    // 다크 모드일 때는 "라이트로 전환" 뜻의 해 아이콘을 보여줌
    if (icon) icon.textContent = isDarkNow() ? "☀" : "☾";
  }

  function initTheme() {
    const root = document.documentElement;
    let saved = null;
    try { saved = localStorage.getItem("theme"); } catch (e) { /* 무시 */ }
    if (saved === "light" || saved === "dark") root.setAttribute("data-theme", saved);
    syncThemeIcon();

    const btn = $("theme-toggle");
    if (!btn) return;
    btn.addEventListener("click", function () {
      const next = isDarkNow() ? "light" : "dark";
      root.setAttribute("data-theme", next);
      try { localStorage.setItem("theme", next); } catch (e) { /* 무시 */ }
      syncThemeIcon();
    });
  }

  /* ---------------- 초기화 ---------------- */

  function init() {
    applyOwner();
    initTheme();
    buildScoreRows();

    // 입력 변화 시 즉시 재계산
    $("battery-form").addEventListener("input", function (e) {
      if (e.target.id === "soh_range") $("soh_percent").value = e.target.value;
      if (e.target.id === "soh_percent") $("soh_range").value = e.target.value;
      render();
    });
    $("battery-form").addEventListener("submit", function (e) { e.preventDefault(); });

    document.querySelectorAll(".chip").forEach((btn) => {
      btn.addEventListener("click", function () { applyPreset(btn.dataset.preset, btn); });
    });

    const first = document.querySelector('.chip[data-preset="A"]');
    if (first) first.setAttribute("aria-pressed", "true");

    render();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
