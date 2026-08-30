/* ==========================================================================
   경로 판정 대시보드

   assets/routing.js 의 판정 엔진과 assets/incoming_data.js 의 입고 데이터를
   받아 화면을 그립니다. 서버 없이 브라우저에서만 동작합니다.
   ========================================================================== */
(function () {
  "use strict";

  var R = window.BatteryRouting;
  var RAW = window.INCOMING_BATTERIES || [];
  var $ = function (id) { return document.getElementById(id); };

  if (!R || !RAW.length) {
    console.error("판정 엔진 또는 입고 데이터를 불러오지 못했습니다.");
    return;
  }

  var RESULTS = RAW.map(R.decide);
  var SUMMARY = R.summarize(RESULTS);

  /* ---------------- 표시 헬퍼 ---------------- */

  function won(n) {
    if (n >= 100000000) return (n / 100000000).toFixed(2) + "억원";
    if (n >= 10000) return Math.round(n / 10000).toLocaleString("ko-KR") + "만원";
    return n.toLocaleString("ko-KR") + "원";
  }

  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  /* ---------------- KPI ---------------- */

  function renderKpis() {
    var el = $("kpi-row");
    var parts = [];

    parts.push(
      '<div class="kpi">' +
        '<span class="kpi-label">입고 총량</span>' +
        '<span class="kpi-value">' + SUMMARY.total + '<span class="unit">대</span></span>' +
        '<span class="kpi-sub">안전성 미달 ' + SUMMARY.safety_failed + '대 포함</span>' +
      '</div>'
    );

    R.ROUTES.forEach(function (route) {
      var b = SUMMARY.routes[route];
      parts.push(
        '<div class="kpi" data-route="' + route + '">' +
          '<span class="kpi-label">' + route + '</span>' +
          '<span class="kpi-value">' + b.count + '<span class="unit">대</span></span>' +
          '<span class="kpi-sub">' + b.share + '% · 평균 SOH ' + b.avg_soh + '%</span>' +
        '</div>'
      );
    });

    parts.push(
      '<div class="kpi">' +
        '<span class="kpi-label">총 추정 잔존가치</span>' +
        '<span class="kpi-value">' + won(SUMMARY.total_value) + '</span>' +
        '<span class="kpi-sub">단가는 가정치</span>' +
      '</div>'
    );

    el.innerHTML = parts.join("");
  }

  /* ---------------- 경로별 누적 막대 + 표 ---------------- */

  function renderRouteStack() {
    var stack = $("route-stack");
    var legend = $("route-legend");
    var tbody = $("route-table-body");

    stack.innerHTML = R.ROUTES.map(function (route) {
      var b = SUMMARY.routes[route];
      if (!b.count) return "";
      // 조각이 좁으면 안쪽 숫자가 안 읽히므로 넓을 때만 직접 라벨을 넣습니다
      var label = b.share >= 12 ? route + " " + b.share + "%" : "";
      return '<div class="stack-seg" data-route="' + route + '"' +
             ' style="flex:' + b.count + '"' +
             ' title="' + route + ' ' + b.count + '대 (' + b.share + '%)">' +
             label + '</div>';
    }).join("");

    legend.innerHTML = R.ROUTES.map(function (route) {
      var b = SUMMARY.routes[route];
      return '<li><span class="swatch" data-route="' + route + '"></span>' +
             route + ' ' + b.count + '대</li>';
    }).join("");

    tbody.innerHTML = R.ROUTES.map(function (route) {
      var b = SUMMARY.routes[route];
      return '<tr>' +
        '<td><span class="route-name"><span class="swatch" data-route="' + route + '"></span>' +
          route + '</span></td>' +
        '<td>' + b.count + '대</td>' +
        '<td>' + b.share + '%</td>' +
        '<td>' + b.avg_soh + '%</td>' +
        '<td>' + won(b.value) + '</td>' +
      '</tr>';
    }).join("");
  }

  /* ---------------- 안전성 미달 사유 ---------------- */

  function renderSafetyChart() {
    var el = $("safety-chart");
    var entries = Object.keys(SUMMARY.safety_reason_counts).map(function (k) {
      return [k, SUMMARY.safety_reason_counts[k]];
    }).sort(function (a, b) { return b[1] - a[1]; });

    if (!entries.length) {
      el.innerHTML = '<p class="hbar-empty">안전성 미달 사례가 없습니다.</p>';
      return;
    }

    var max = entries[0][1];
    el.innerHTML = entries.map(function (e) {
      return '<div class="hbar-row">' +
        '<div class="hbar-top">' +
          '<span class="hbar-name">' + esc(e[0]) + '</span>' +
          '<span class="hbar-val">' + e[1] + '건</span>' +
        '</div>' +
        '<div class="hbar-track"><div class="hbar-fill" style="width:' +
          (e[1] / max * 100) + '%"></div></div>' +
      '</div>';
    }).join("");
  }

  /* ---------------- SOH 구간별 경로 분포 ---------------- */

  var SOH_BINS = [
    { label: "90% 이상", min: 90, max: 1000 },
    { label: "80 – 90%", min: 80, max: 90 },
    { label: "70 – 80%", min: 70, max: 80 },
    { label: "60 – 70%", min: 60, max: 70 },
    { label: "60% 미만", min: -1, max: 60 }
  ];

  function renderSohChart() {
    var el = $("soh-chart");

    el.innerHTML = SOH_BINS.map(function (bin) {
      var inBin = RESULTS.filter(function (r) {
        return r.soh >= bin.min && r.soh < bin.max;
      });
      var counts = {};
      R.ROUTES.forEach(function (rt) { counts[rt] = 0; });
      inBin.forEach(function (r) { counts[r.route] += 1; });

      var segs = R.ROUTES.map(function (rt) {
        if (!counts[rt]) return "";
        return '<div class="soh-seg" data-route="' + rt + '" style="flex:' + counts[rt] + '"' +
               ' title="' + bin.label + ' · ' + rt + ' ' + counts[rt] + '대"></div>';
      }).join("");

      return '<div class="soh-row">' +
        '<span class="soh-label">' + bin.label + '</span>' +
        '<div class="soh-track">' + (segs || "") + '</div>' +
        '<span class="soh-total">' + inBin.length + '대</span>' +
      '</div>';
    }).join("");

    $("soh-legend").innerHTML = R.ROUTES.map(function (route) {
      return '<li><span class="swatch" data-route="' + route + '"></span>' + route + '</li>';
    }).join("");
  }

  /* ---------------- 핵심 사례 ---------------- */

  function renderInsight() {
    var overridden = RESULTS.filter(function (r) {
      return !r.safety_passed && r.soh >= R.SOH_THRESHOLDS.remanufacture;
    }).sort(function (a, b) { return b.soh - a.soh; });

    $("insight-summary").textContent =
      overridden.length
        ? "SOH " + R.SOH_THRESHOLDS.remanufacture + "% 기준은 넘겼지만 안전성 게이트에서 걸린 배터리가 " +
          overridden.length + "대 있습니다. 잔존 용량만으로 판단했다면 전기차에 다시 들어갔을 배터리입니다."
        : "이번 입고분에는 해당 사례가 없습니다.";

    $("insight-list").innerHTML = overridden.slice(0, 6).map(function (r) {
      return '<div class="insight-item">' +
        '<div class="ii-top">' +
          '<span class="ii-id">' + esc(r.battery_id) + '</span>' +
          '<span class="ii-soh">SOH ' + r.soh.toFixed(1) + '%</span>' +
          '<span class="ii-route">→ 재활용</span>' +
        '</div>' +
        '<div class="ii-reason">' + esc(r.safety_reasons.join(" · ")) + '</div>' +
      '</div>';
    }).join("");
  }

  /* ---------------- 배터리 표 ---------------- */

  var state = { filter: "전체", sortKey: "battery_id", sortDir: 1 };

  function visibleRows() {
    var rows = state.filter === "전체"
      ? RESULTS.slice()
      : RESULTS.filter(function (r) { return r.route === state.filter; });

    var key = state.sortKey, dir = state.sortDir;
    rows.sort(function (a, b) {
      var x = a[key], y = b[key];
      if (typeof x === "number" && typeof y === "number") return (x - y) * dir;
      return String(x).localeCompare(String(y), "ko") * dir;
    });
    return rows;
  }

  function renderTable() {
    var rows = visibleRows();
    $("filter-count").textContent = rows.length + "대 표시 중";

    $("table-body").innerHTML = rows.map(function (r) {
      var flags = "";
      if (!r.safety_passed) flags = '<span class="flag-unsafe">안전미달</span>';
      else if (r.downgraded) flags = '<span class="flag-down">강등</span>';

      return '<tr>' +
        '<td>' + esc(r.battery_id) + '</td>' +
        '<td>' + esc(r.vehicle) + '</td>' +
        '<td class="num">' + r.soh.toFixed(1) + '%</td>' +
        '<td class="num">' + Math.round(r.deviation_mv) + 'mV</td>' +
        '<td class="num">' + r.max_temp.toFixed(0) + '℃</td>' +
        '<td class="num">' + r.bms_errors + '회</td>' +
        '<td><span class="route-chip" data-route="' + r.route + '">' + r.route + '</span>' + flags + '</td>' +
        '<td class="num">' + won(r.estimated_value_krw) + '</td>' +
        '<td class="reason">' + esc(r.reason_text) + '</td>' +
      '</tr>';
    }).join("");
  }

  function initTableControls() {
    document.querySelectorAll(".filter-row .chip").forEach(function (btn) {
      btn.addEventListener("click", function () {
        state.filter = btn.dataset.filter;
        document.querySelectorAll(".filter-row .chip").forEach(function (c) {
          c.setAttribute("aria-pressed", String(c === btn));
        });
        renderTable();
      });
    });

    document.querySelectorAll("#battery-table thead th[data-sort]").forEach(function (th) {
      th.addEventListener("click", function () {
        var key = th.dataset.sort;
        state.sortDir = (state.sortKey === key) ? -state.sortDir : 1;
        state.sortKey = key;

        document.querySelectorAll("#battery-table thead th").forEach(function (o) {
          o.removeAttribute("aria-sort");
        });
        th.setAttribute("aria-sort", state.sortDir === 1 ? "ascending" : "descending");
        renderTable();
      });
    });
  }

  /* ---------------- 소유자 정보 / 테마 ---------------- */

  function applyOwner() {
    var o = $("owner");
    if (!o) return;
    if ($("footer-name")) $("footer-name").textContent = o.dataset.name;
    if ($("year")) $("year").textContent = new Date().getFullYear();
  }

  function isDarkNow() {
    var stamped = document.documentElement.getAttribute("data-theme");
    if (stamped === "dark") return true;
    if (stamped === "light") return false;
    return window.matchMedia("(prefers-color-scheme: dark)").matches;
  }

  function initTheme() {
    var root = document.documentElement;
    var saved = null;
    try { saved = localStorage.getItem("theme"); } catch (e) { /* 무시 */ }
    if (saved === "light" || saved === "dark") root.setAttribute("data-theme", saved);

    var icon = $("theme-icon");
    if (icon) icon.textContent = isDarkNow() ? "☀" : "☾";

    var btn = $("theme-toggle");
    if (!btn) return;
    btn.addEventListener("click", function () {
      var next = isDarkNow() ? "light" : "dark";
      root.setAttribute("data-theme", next);
      try { localStorage.setItem("theme", next); } catch (e) { /* 무시 */ }
      if (icon) icon.textContent = isDarkNow() ? "☀" : "☾";
    });
  }

  /* ---------------- 초기화 ---------------- */

  function init() {
    applyOwner();
    initTheme();
    renderKpis();
    renderRouteStack();
    renderSafetyChart();
    renderSohChart();
    renderInsight();
    initTableControls();
    renderTable();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
