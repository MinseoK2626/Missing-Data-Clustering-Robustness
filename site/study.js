const $ = (selector, parent = document) => parent.querySelector(selector);
const $$ = (selector, parent = document) => [...parent.querySelectorAll(selector)];
const fmt = (value, digits = 3) => Number.isFinite(value)
  ? value.toLocaleString("en-US", {minimumFractionDigits: digits, maximumFractionDigits: digits}) : "—";
const count = value => fmt(value, 0);
const pct = (value, digits = 1) => Number.isFinite(value) ? `${fmt(value * 100, digits)}%` : "—";
const escape = value => String(value).replace(/[&<>"']/g, character => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
})[character]);
const rateLabel = rate => pct(+rate, 0);
const mechanisms = ["MCAR", "MAR", "MNAR"];
const rates = [.05, .10, .20, .30, .40];
const methods = ["zero", "median", "knn", "iterative"];
const methodLabel = {zero: "Zero", median: "Median", knn: "KNN", iterative: "Iterative"};
const metricLabel = {
  ari: "Benchmark ARI", silhouette: "Silhouette", change_rate: "Assignment change rate",
  realized_product_rate: "Realized product missingness", realized_overall_rate: "Overall missingness",
  centroid_displacement: "Centroid displacement", rmse: "Masked-cell RMSE",
};
const metrics = Object.keys(metricLabel);
const palette = {zero: "#292a49", median: "#635384", knn: "#7664a9", iterative: "#425f75"};
const chartFormat = (value, metric) => (metric.includes("rate") ? pct(value) : fmt(value));
const cluster = value => ({html: `<span class="cluster cluster-${value}">Cluster ${value + 1}</span>`});
const navLinks = [["overview", "Overview"], ["abstract", "Abstract"], ["questions", "Research questions"],
  ["methodology", "Methodology"], ["lab", "Experiment lab"], ["results", "Results"],
  ["uncertainty", "Uncertainty analysis"], ["discussion", "Discussion"],
  ["reproducibility", "Reproducibility"], ["references", "References"]];
const payload = new Map();

function get(file) {
  if (!payload.has(file)) {
    payload.set(file, fetch(`data/${file}.json`).then(response => {
      if (!response.ok) throw Error(`Failed to load ${file} (${response.status})`);
      return response.json();
    }).catch(error => {
      payload.delete(file);
      throw error;
    }));
  }
  return payload.get(file);
}

function select(id, label, values, stringify = value => value) {
  return `<label for="${id}">${label}<select id="${id}">${values.map(value =>
    `<option value="${escape(value)}">${escape(stringify(value))}</option>`).join("")}</select></label>`;
}

function table(headings, rows, label) {
  return `<div class="scroller" tabindex="0" role="region" aria-label="${escape(label)}"><table aria-label="${escape(label)}">
  <thead><tr>${headings.map(title => `<th scope="col">${escape(title)}</th>`).join("")}</tr></thead>
  <tbody>${rows.map(row => `<tr>${row.map(cell => typeof cell === "object"
    ? `<td class="${cell.mask ? "masked" : ""}">${cell.html}</td>`
    : `<td>${escape(cell)}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
}

function configName(row) {
  return `${row.mechanism} · ${rateLabel(row.target_rate)} · ${methodLabel[row.method]}`;
}

function dots(container, points, xLabel, yLabel, bounds, formatters, detail, xGuide, yGuide) {
  if (!points.length) {
    container.innerHTML = "<p>No completed runs for this selection.</p>";
    return;
  }
  const width = 840, height = 375, left = 79, right = 28, top = 18, bottom = 61;
  const [xMin, xMax, yMin, yMax] = bounds;
  const x = value => left + (width - left - right) * (value - xMin) / (xMax - xMin);
  const y = value => height - bottom - (height - bottom - top) * (value - yMin) / (yMax - yMin);
  const svgText = (xPos, yPos, text, extra = "") => `<text x="${xPos}" y="${yPos}" ${extra}>${escape(text)}</text>`;
  const ticks = Array.from({length: 6}, (_, index) => index / 5);
  container.innerHTML = `<div class="chart">
    <svg viewBox="0 0 ${width} ${height}" role="img" aria-label="${escape(`${yLabel} against ${xLabel}`)}">
    ${ticks.map(fraction => {
      const xValue = xMin + fraction * (xMax - xMin), yValue = yMin + fraction * (yMax - yMin);
      return `<path d="M${left} ${y(yValue)}H${width-right}" stroke="#e9e5ef"/>` +
        svgText(left - 9, y(yValue) + 4, formatters[1](yValue), 'text-anchor="end"') +
        svgText(x(xValue), height - bottom + 22, formatters[0](xValue), 'text-anchor="middle"');
    }).join("")}
    ${xGuide === undefined ? "" : `<path d="M${x(xGuide)} ${top}V${height-bottom}" stroke="#8b80a4" stroke-dasharray="5 5"/>`}
    ${yGuide === undefined ? "" : `<path d="M${left} ${y(yGuide)}H${width-right}" stroke="#8b80a4" stroke-dasharray="5 5"/>`}
    ${points.map((point, index) => `<circle cx="${x(point.x)}" cy="${y(point.y)}" r="${point.highlight ? 4 : 2.7}" fill="${point.highlight ? "#6543a7" : "#a29bb4"}" opacity="${point.highlight ? .85 : .40}" data-point="${index}"><title>${escape(detail(point))}</title></circle>`).join("")}
    ${svgText((left + width - right) / 2, height - 9, xLabel, 'text-anchor="middle"')}
    ${svgText(16, (height - bottom + top) / 2, yLabel, `text-anchor="middle" transform="rotate(-90 16 ${(height - bottom + top) / 2})"`)}
    </svg><p class="chart-status">Hover over a point to inspect its result.</p></div>`;
  container.onpointerover = event => {
    const index = event.target.dataset?.point;
    if (index !== undefined) $(".chart-status", container).textContent = detail(points[+index]);
  };
}

function intervals(rows, metric) {
  const entries = rows.filter(row => row.metrics[metric].n);
  if (!entries.length) return "";
  const width = 840, left = 106, right = 75, height = 75 + 57 * entries.length;
  const statistics = entries.map(row => row.metrics[metric]);
  const lower = Math.min(...statistics.map(stat => stat.q05));
  const upper = Math.max(...statistics.map(stat => stat.q95));
  const spread = (upper - lower || 1) * .08;
  const axisMin = lower - spread, axisMax = upper + spread;
  const x = value => left + (width-left-right) * (value-axisMin) / (axisMax-axisMin);
  const tick = Array.from({length: 5}, (_, index) => axisMin + (axisMax-axisMin) * index / 4);
  return `<div class="chart"><svg viewBox="0 0 ${width} ${height}" role="group" aria-label="${metricLabel[metric]} distributions by method">
    ${tick.map(value => `<line x1="${x(value)}" y1="14" x2="${x(value)}" y2="${height-50}" stroke="#eeeaf3"/>
      <text x="${x(value)}" y="${height-30}" text-anchor="middle">${chartFormat(value, metric)}</text>`).join("")}
    ${entries.map((row, index) => {
      const stat = row.metrics[metric], y = 35 + index * 57, color = palette[row.method];
      const tooltip = `${configName(row)}. Median ${chartFormat(stat.median, metric)}, mean ${chartFormat(stat.mean, metric)}, CI ${chartFormat(stat.low, metric)} to ${chartFormat(stat.high, metric)}`;
      return `<g tabindex="0" role="img" aria-label="${escape(tooltip)}"><title>${escape(tooltip)}</title>
        <text x="14" y="${y+4}">${methodLabel[row.method]}</text>
        <path d="M${x(stat.q05)} ${y}H${x(stat.q95)}" stroke="${color}" stroke-width="2"/>
        <rect x="${x(stat.q25)}" y="${y-8}" width="${Math.max(1, x(stat.q75)-x(stat.q25))}" height="16" fill="#ded6ed" stroke="${color}"/>
        <path d="M${x(stat.median)} ${y-10}v20" stroke="${color}" stroke-width="2"/>
        ${stat.low === null ? "" : `<path d="M${x(stat.low)} ${y+16}H${x(stat.high)}" stroke="#6543a7" stroke-width="3"/>`}
        <circle cx="${x(stat.mean)}" cy="${y+16}" r="4" fill="#6543a7"/></g>`;
    }).join("")}</svg></div>`;
}

function initNavigation() {
  $$("[data-navigation]").forEach(nav => {
    nav.innerHTML = navLinks.map(([anchor, title]) => `<a href="#${anchor}">${title}</a>`).join("");
    nav.addEventListener("click", event => {
      if (event.target.closest("a")) event.target.closest("details")?.removeAttribute("open");
    });
  });
  function activeSection() {
    const active = navLinks.filter(([anchor]) => document.getElementById(anchor).getBoundingClientRect().top <= 140).at(-1)?.[0] || "overview";
    $$("[data-navigation] a").forEach(link => {
      if (link.hash === `#${active}`) link.setAttribute("aria-current", "location");
      else link.removeAttribute("aria-current");
    });
  }
  addEventListener("scroll", activeSection, {passive: true});
  activeSection();
}

function labs(facts) {
  const controls = $("#lab-controls"), result = $("#lab-result");
  controls.innerHTML = select("lab-mech", "Mechanism", mechanisms)
    + select("lab-rate", "Target product masking", rates, rateLabel)
    + select("lab-metric", "Chart metric", metrics, key => metricLabel[key])
    + select("lab-view", "Show", ["Aggregate", "Individual seeds"])
    + `<fieldset><legend>Imputation methods</legend>${methods.map(method =>
      `<label class="check"><input type="checkbox" value="${method}" checked> ${methodLabel[method]}</label>`).join("")}</fieldset>`
    + '<button id="lab-reset" type="button">Reset</button>';
  const rowsFor = () => facts.summary.filter(row => row.mechanism === $("#lab-mech").value
    && row.target_rate === +$("#lab-rate").value && $(`input[value="${row.method}"]`, controls).checked);
  let renderRequest = 0;
  async function update() {
    const request = ++renderRequest, rows = rowsFor(), metric = $("#lab-metric").value;
    if (!rows.length) {
      result.innerHTML = "<p>Choose one or more imputation methods.</p>";
      return;
    }
    if ($("#lab-view").value === "Individual seeds") {
      result.innerHTML = '<p role="status">Loading seed outcomes…</p>';
      try {
        const runs = await get("runs");
        if (request !== renderRequest) return;
        const selected = new Set(rows.map(configName));
        const matching = runs.filter(row => selected.has(configName(row)));
        result.innerHTML = table(["Seed", "Method", metricLabel[metric], "ARI", "Silhouette", "Changed", "Product missing", "All cells missing"],
          matching.map(row => [row.seed, methodLabel[row.method], chartFormat(row[metric], metric), fmt(row.ari),
            fmt(row.silhouette), pct(row.change_rate), pct(row.realized_product_rate), pct(row.realized_overall_rate)]),
          "Seed-level experimental results");
      } catch (error) {
        if (request === renderRequest) result.textContent = error.message;
      }
      return;
    }
    result.innerHTML = intervals(rows, metric) +
      table(["Method", "Mean", "Median", "95% CI", "SD", "IQR", "P05–P95", "Runs"],
        rows.map(row => {
          const stat = row.metrics[metric], display = value => chartFormat(value, metric);
          return [methodLabel[row.method], display(stat.mean), display(stat.median),
            `${display(stat.low)} to ${display(stat.high)}`, display(stat.sd), display(stat.iqr),
            `${display(stat.q05)} to ${display(stat.q95)}`, `${row.completed} / ${row.planned}`];
        }), "Selected metric and uncertainty") +
      table(["Method", "Mean ARI", "Median ARI", "Silhouette", "Assignments changed", "Product missing", "All cells missing"],
        rows.map(row => [methodLabel[row.method], fmt(row.metrics.ari.mean), fmt(row.metrics.ari.median),
          fmt(row.metrics.silhouette.mean), pct(row.metrics.change_rate.mean),
          pct(row.metrics.realized_product_rate.mean), pct(row.metrics.realized_overall_rate.mean)]), "Core diagnostic metrics");
  }
  function reset() {
    $("#lab-mech").value = "MCAR";
    $("#lab-rate").value = .30;
    $("#lab-metric").value = "ari";
    $("#lab-view").value = "Aggregate";
    $$("input", controls).forEach(box => { box.checked = true; });
    update();
  }
  controls.addEventListener("change", update);
  $("#lab-reset").addEventListener("click", reset);
  reset();
  function go(row, metric = "ari") {
    $("#lab-mech").value = row.mechanism;
    $("#lab-rate").value = row.target_rate;
    $("#lab-metric").value = metric;
    $("#lab-view").value = "Aggregate";
    $$("input", controls).forEach(input => { input.checked = input.value === row.method; });
    update();
    location.hash = "lab";
    $("#lab-mech").focus({preventScroll: true});
  }
  $("#design-equation").textContent = `${facts.design.seed_target} seeds × ${rates.length} levels × ${mechanisms.length} mechanisms × ${methods.length} methods = ${count(facts.design.planned)} planned runs. Select a configuration to open its lab results.`;
  $("#design-table").innerHTML = table(["Configuration", "Planned", "Usable", "Failed", "Convergence warnings", "Coverage"],
    facts.summary.map((row, index) => [{html: `<button type="button" data-config="${index}">${configName(row)}</button>`},
      row.planned, row.completed, row.failed, facts.design.warnings === null ? "Untracked" : row.warnings,
      pct((row.completed + row.failed) / row.planned, 0)]), "Factorial design coverage");
  $("#design-table").addEventListener("click", event => {
    const button = event.target.closest("[data-config]");
    if (button) go(facts.summary[+button.dataset.config]);
  });
  return go;
}

function heatmap(facts, go) {
  $("#heat-controls").innerHTML = select("heat-metric", "Heatmap metric", metrics, key => metricLabel[key]);
  function draw() {
    const metric = $("#heat-metric").value;
    const means = facts.summary.map(row => row.metrics[metric].mean).filter(Number.isFinite);
    const min = Math.min(...means), max = Math.max(...means);
    $("#heatmap").innerHTML = table(["Mechanism", "Target", ...methods.map(method => methodLabel[method])],
      mechanisms.flatMap(mechanism => rates.map(rate => [
        mechanism, rateLabel(rate), ...methods.map(method => {
          const index = facts.summary.findIndex(row => row.method === method && row.mechanism === mechanism && row.target_rate === rate);
          const stats = facts.summary[index].metrics[metric];
          const level = Number.isFinite(stats.mean) ? Math.round(100 * (stats.mean - min) / (max-min || 1)) : 0;
          const tooltip = `${configName(facts.summary[index])}. Mean ${chartFormat(stats.mean, metric)}. 95% CI ${chartFormat(stats.low, metric)} to ${chartFormat(stats.high, metric)}`;
          return {html: `<button type="button" data-heat="${index}" aria-label="${escape(tooltip)}" title="${escape(tooltip)}"
            style="background:hsl(259 40% ${98-level*.23}%)">${chartFormat(stats.mean, metric)}</button>`};
        }),
      ])), "Mean outcomes by mechanism, masking level and imputation");
  }
  $("#heat-metric").addEventListener("change", draw);
  $("#heatmap").addEventListener("click", event => {
    const button = event.target.closest("[data-heat]");
    if (button) go(facts.summary[+button.dataset.heat], $("#heat-metric").value);
  });
  draw();
}

function summaries(facts) {
  const d = facts.design, validation = facts.validation;
  const scope = [[d.completed, "Usable factorial runs"], [d.seeds, "Completed seeds"], [d.configurations, "Factorial designs"],
    [mechanisms.length, "Missingness mechanisms"], [methods.length, "Imputation strategies"],
    [Math.max(...facts.sample.map(row => row.stores)), "Largest training cohort"]];
  $("#study-counts").innerHTML = scope.map(([number, label]) => `<div><dt>${label}</dt><dd>${count(number)}</dd></div>`).join("");
  $("#study-status").textContent = `${facts.version} · ${count(d.completed)} usable of ${count(d.planned)} planned · ${count(d.failures)} failed · ${count(d.unattempted)} unattempted${d.warnings === null ? "" : ` · ${count(d.warnings)} usable runs with convergence warnings`}`;
  const matched = facts.paired.find(row => row.mechanism === "MCAR" && row.target_rate === .30 && row.left === "zero" && row.right === "iterative");
  $("#abstract-results").textContent = `The ${facts.version.toLowerCase()} compares three masking mechanisms, five product-cell masking targets and four imputation strategies. In ${count(validation.changed_ten_percent)} of ${count(d.completed)} usable runs, silhouette improved even as at least 10% of aligned store assignments changed. Held-out training-size and model confidence comparisons draw on separately identified original-study cohorts.`;
  $("#finding-one").textContent = `At 30% MCAR, iterative minus zero imputation changed mean benchmark ARI by ${fmt(-matched.mean)} (95% matched seed-bootstrap interval ${fmt(-matched.high)} to ${fmt(-matched.low)}; ${matched.n} seed pairs).`;
  $("#finding-two").textContent = `Silhouette improved in ${count(validation.improved)} of ${count(d.completed)} runs (${pct(validation.improved / d.completed)}). Of the improved runs, ${count(validation.changed_ten_percent)} changed at least 10% of assignments and ${count(validation.ari_below_half)} had ARI below 0.50.`;
  const mnar = facts.sample.filter(row => row.mechanism === "MNAR" && row.method === "zero");
  const small = mnar[0], large = mnar.at(-1);
  $("#finding-three").textContent = `Across ${count(facts.sample_runs)} original held-out runs, the 30% MNAR zero-fill mean rose from ${fmt(small.mean)} at ${count(small.stores)} stores to ${fmt(large.mean)} at ${count(large.stores)}, while across-seed SD fell from ${fmt(small.sd)} to ${fmt(large.sd)}.`;
  if (facts.version.startsWith("Original")) {
    $("[data-results]").href = "results/tables/factorial.csv";
    $("[data-report]").href = $("[data-report]").href.replace("expanded_report.md", "research_report.md");
  } else if (facts.pdf) {
    $("[data-download]").hidden = false;
  }
}

async function validationScatter(go, facts) {
  const controls = $("#scatter-controls"), chart = $("#validation-scatter");
  controls.innerHTML = select("scatter-mech", "Mechanism", mechanisms)
    + select("scatter-method", "Method", ["all", ...methods], value => methodLabel[value] || "All methods")
    + '<label class="check"><input type="checkbox" id="scatter-highlight"> Highlighted cases only</label>';
  const runs = await get("runs");
  function draw() {
    const selected = $("#scatter-method").value;
    const points = runs.filter(row => row.mechanism === $("#scatter-mech").value
      && (selected === "all" || selected === row.method))
      .map(row => ({x: row.silhouette_delta, y: row.change_rate, row,
        highlight: row.silhouette_delta > 0 && row.change_rate >= .10}))
      .filter(point => !$("#scatter-highlight").checked || point.highlight);
    const xLimit = Math.max(.01, ...points.map(point => Math.abs(point.x))) * 1.08;
    const yLimit = Math.max(.11, ...points.map(point => point.y)) * 1.06;
    const description = ({row}) => `Seed ${row.seed} · ${configName(row)} · silhouette gain ${fmt(row.silhouette_delta)} · changed ${pct(row.change_rate)} · ARI ${fmt(row.ari)}`;
    dots(chart, points, "Change in silhouette", "Assignments changed", [-xLimit, xLimit, 0, yLimit], [value => fmt(value, 2), pct], description, 0, .10);
    if (!points.length) return;
    const lookup = document.createElement("div");
    lookup.className = "controls";
    const focus = points.filter(point => point.highlight);
    const inspect = focus.length ? focus : points;
    lookup.innerHTML = select("scatter-example", "Inspect seed and configuration", inspect.map((_, index) => index),
      index => `Seed ${inspect[index].row.seed} · ${configName(inspect[index].row)}`)
      + '<button type="button" id="scatter-open">Open configuration in lab</button>';
    chart.append(lookup);
    function update() {
      $(".chart-status", chart).textContent = description(inspect[+$("#scatter-example").value]);
    }
    $("#scatter-example").addEventListener("change", update);
    $("#scatter-open").addEventListener("click", () => {
      const point = inspect[+$("#scatter-example").value];
      go(facts.summary.find(row => configName(row) === configName(point.row)));
    });
  }
  controls.addEventListener("change", draw);
  draw();
}

function sampleChart(facts) {
  $("#sample-controls").innerHTML = select("sample-mech", "Mechanism", mechanisms)
    + '<label class="check"><input id="sample-seeds" type="checkbox" checked> Show individual seeds</label>';
  function draw() {
    const series = facts.sample.filter(row => row.mechanism === $("#sample-mech").value);
    const allPoints = series.flatMap(row => row.seeds.map(seed => seed.ari));
    const low = Math.min(.2, ...allPoints), high = 1;
    const x = n => 84 + 700 * (Math.log(n) - Math.log(500)) / (Math.log(18000) - Math.log(500));
    const y = value => 310 - (value-low) / (high-low) * 278;
    const sizeTicks = [...new Set(series.map(row => row.stores))];
    const seedPoints = $("#sample-seeds").checked;
    $("#sample-chart").innerHTML = `<div class="chart"><svg viewBox="0 0 840 380" role="group" aria-label="Held-out ARI by sample size">
      ${Array.from({length: 5}, (_, i) => low + (high-low)*i/4).map(tick =>
        `<path d="M84 ${y(tick)}H790" stroke="#ded9eb"/><text x="68" y="${y(tick)+4}" text-anchor="end">${fmt(tick, 2)}</text>`).join("")}
      ${sizeTicks.map(n => `<text x="${x(n)}" y="337" text-anchor="middle">${count(n)}</text>`).join("")}
      ${["zero", "median"].map((method, index) => {
        const rows = series.filter(row => row.method === method), dx = index ? 4 : -4, color = palette[method];
        const path = rows.map((row, i) => `${i ? "L" : "M"}${x(row.stores)+dx} ${y(row.mean)}`).join(" ");
        return `<path d="${path}" fill="none" stroke="${color}" stroke-width="2"/>` + rows.map(row => {
          const tooltip = `${methodLabel[method]}, ${count(row.stores)} stores. ARI ${fmt(row.mean)}; 95% CI ${fmt(row.low)} to ${fmt(row.high)}`;
          return `${seedPoints ? row.seeds.map(seed => `<circle cx="${x(row.stores)+dx}" cy="${y(seed.ari)}" r="4" opacity=".30" fill="${color}"><title>Seed ${seed.seed} · ARI ${fmt(seed.ari)}</title></circle>`).join("") : ""}
            <g tabindex="0" role="img" aria-label="${escape(tooltip)}"><title>${escape(tooltip)}</title>
            <path d="M${x(row.stores)+dx} ${y(row.high)}V${y(row.low)}" stroke="${color}" stroke-width="3"/>
            <circle cx="${x(row.stores)+dx}" cy="${y(row.mean)}" r="5" fill="${color}"/></g>`;
        }).join("");
      }).join("")}
      <text x="432" y="366" text-anchor="middle">Training stores (log scale)</text>
      <text x="16" y="175" text-anchor="middle" transform="rotate(-90 16 175)">Held-out ARI</text>
    </svg><div class="chart-key"><span><i style="background:${palette.zero}"></i>Zero</span><span><i style="background:${palette.median}"></i>Median</span></div></div>`
    + table(["Method", "Training stores", "Mean ARI", "95% CI", "Seed SD", "Runs"], series.map(row =>
      [methodLabel[row.method], count(row.stores), fmt(row.mean), `${fmt(row.low)} to ${fmt(row.high)}`, fmt(row.sd), row.n]), "Held-out sample outcomes");
  }
  $("#sample-controls").addEventListener("change", draw);
  $("#sample-mech").value = "MNAR";
  draw();
}

function pairedPanel(facts) {
  $("#pair-controls").innerHTML = select("pair-mech", "Mechanism", mechanisms)
    + select("pair-rate", "Target product masking", rates, rateLabel);
  function draw() {
    const matches = row => row.mechanism === $("#pair-mech").value && row.target_rate === +$("#pair-rate").value;
    const ranking = facts.ranking.filter(matches);
    const groups = facts.summary.filter(matches);
    const pairs = facts.paired.filter(matches);
    const extent = Math.max(.025, ...pairs.flatMap(row => [Math.abs(row.low || 0), Math.abs(row.high || 0)]));
    const x = value => 445 + 310 * value / extent;
    $("#paired").innerHTML = `<div class="chart"><svg viewBox="0 0 840 255" role="group" aria-label="Mean paired differences in ARI">
      <path d="M445 9V208" stroke="#a69acb" stroke-dasharray="4 4"/>
      ${[-extent, -extent / 2, 0, extent / 2, extent].map(tick =>
        `<text x="${x(tick)}" y="224" text-anchor="middle">${fmt(tick)}</text>`).join("")}
      ${pairs.filter(row => row.n).map((row, index) => {
        const y = 24 + 30 * index;
        const name = `${methodLabel[row.left]} − ${methodLabel[row.right]}`;
        const description = `${name}: ${fmt(row.mean)} ARI, CI ${fmt(row.low)} to ${fmt(row.high)}, ${row.n} pairs`;
        return `<g tabindex="0" role="img" aria-label="${description}"><title>${description}</title>
          <text x="10" y="${y+4}">${name}</text>
          ${row.low === null ? "" : `<path d="M${x(row.low)} ${y}H${x(row.high)}" stroke="#655394" stroke-width="3"/>`}
          <circle cx="${x(row.mean)}" cy="${y}" r="5" fill="#49377a"/></g>`;
      }).join("")}
      <text x="445" y="246" text-anchor="middle">Left method minus right method (ARI units)</text></svg></div>`
    + table(["Method", "Median ARI", "5th percentile", "Best ARI share", "Complete seed groups"],
      groups.map(row => {
        const rank = ranking.find(rankingRow => rankingRow.method === row.method);
        return [methodLabel[row.method], fmt(row.metrics.ari.median), fmt(row.metrics.ari.q05), pct(rank.win_share), rank.n];
      }), "Seed-level ranks and lower-tail agreement")
    + table(["Contrast", "Mean ARI difference", "95% CI", "Paired seeds"],
      pairs.map(row => [`${methodLabel[row.left]} − ${methodLabel[row.right]}`, fmt(row.mean),
        `${fmt(row.low)} to ${fmt(row.high)}`, row.n]), "Paired comparison estimates");
  }
  $("#pair-rate").value = .30;
  $("#pair-controls").addEventListener("change", draw);
  draw();
}

const featureLabels = value => value.replaceAll("_", " ");
async function demonstration() {
  const root = $("#demo"), data = await get("demo");
  const stages = ["Complete values", "Missingness mask", "Observed values", "Imputed values", "Cluster assignments"];
  root.innerHTML = '<div class="controls">'
    + select("demo-mech", "Mechanism", mechanisms)
    + select("demo-rate", "Target product masking", rates, rateLabel)
    + select("demo-method", "Imputation", methods, value => methodLabel[value])
    + select("demo-stage", "Pipeline stage", stages) + '</div><div id="demo-result"></div>';
  const explanations = {
    MCAR: "Each eligible cell has the same masking probability.",
    MAR: "Lower observed traffic and higher observed evening share raise masking probability.",
    MNAR: "Low underlying product sales raise masking probability. Those sales may become unobserved.",
  };
  function draw() {
    const mechanism = $("#demo-mech").value, level = $("#demo-rate").value, method = $("#demo-method").value;
    const dataCase = data.cases[`${mechanism}/${Math.round(+level * 100)}`];
    const stage = $("#demo-stage").value;
    const prefix = `<p>${explanations[mechanism]}</p>`;
    if (stage === "Cluster assignments") {
      $("#demo-result").innerHTML = prefix + table(["Store", "Reference", "After imputation"], data.ids.map((id, i) =>
        [id, cluster(data.reference[i]), cluster(dataCase.assignments[method][i])]), "Aligned cluster assignments");
      return;
    }
    const values = stage === "Complete values" ? data.complete
      : stage === "Observed values" ? dataCase.observed : dataCase.values[method];
    $("#demo-result").innerHTML = prefix + table(["Store", ...data.columns.map(featureLabels)],
      values.map((row, i) => [data.ids[i], ...row.map((value, j) => {
        const masked = dataCase.mask[i][j];
        const display = stage === "Missingness mask" ? (masked ? "Masked" : "Observed")
          : value === null ? "Missing" : fmt(value, 2);
        return {html: escape(display), mask: masked && stage !== "Complete values"};
      })]), stage);
  }
  root.addEventListener("change", draw);
  $("#demo-mech").value = "MAR";
  $("#demo-rate").value = .30;
  $("#demo-stage").value = "Missingness mask";
  draw();
  root.setAttribute("aria-busy", "false");
}

async function uncertainty() {
  const root = $("#uncertainty-content"), data = await get("uncertainty");
  const stores = new Map(data.stores.map(row => [row.store_id, row]));
  root.innerHTML = `<p><strong>${count(data.discordant)} of ${count(stores.size)} stores</strong> had high posterior confidence and low cross-scenario stability.</p>
  <div class="controls"><label class="check"><input type="checkbox" id="discordance-only"> Show only these stores</label></div>
  <div id="uncertainty-plot"></div><h3>Inspect a synthetic store</h3>
  <p>The selector includes stores where confidence and stability disagree, stores close to a complete-data boundary, and stores with high stability. The values below use the same representative 30% MNAR mask for all four methods.</p>
  <div class="controls">${select("store-id", "Synthetic store", data.detail.ids, id => `Store ${id} · ${stores.get(id).profile}`)}</div>
  <div id="store-detail" aria-live="polite"></div><h3>Shift the assumptions about missing sales</h3>
  <p>The original sensitivity analysis perturbed masked iterative estimates in positive-sales IQR units before refitting K-means. This tests how recommendations depend on assumed hidden values.</p>
  ${table(["IQR shift", "Benchmark ARI", "Assignments changed vs. baseline", "Decision changed"],
    data.sensitivity.map(row => [fmt(row.iqr_shift, 2), fmt(row.ari), pct(row.change_from_base), pct(row.decision_change_rate)]),
    "Original MNAR sensitivity analysis")}`;
  function drawPlot() {
    const points = data.stores.filter(row => !$("#discordance-only").checked || row.discordant)
      .map(row => ({x: row.gmm_max_posterior, y: row.stability, row, highlight: row.discordant}))
      .sort((left, right) => Number(left.highlight) - Number(right.highlight));
    dots($("#uncertainty-plot"), points, "Maximum GMM posterior", "K-means scenario stability",
      [.25, 1, .25, 1], [pct, pct], ({row}) =>
        `Store ${row.store_id} · ${row.profile} · posterior ${pct(row.gmm_max_posterior)} · stability ${pct(row.stability)}`, .80, .60);
  }
  function detail() {
    const id = +$("#store-id").value, i = data.detail.ids.indexOf(id), row = stores.get(id);
    const d = data.detail;
    $("#store-detail").innerHTML = `<p><strong>Store ${id}</strong> · ${escape(row.profile)} · GMM posterior ${pct(row.gmm_max_posterior)} · scenario stability ${pct(row.stability)} · changes vs. reference ${pct(row.change_frequency)}</p>`
    + table(["Feature", "Complete", "Status", ...methods.map(method => methodLabel[method])],
      d.columns.map((column, j) => {
        const masked = d.mask[i][j];
        return [featureLabels(column), fmt(d.complete[i][j], 2),
          {html: masked ? "Masked" : "Observed", mask: masked},
          ...methods.map(method => ({html: fmt(d.values[method][i][j], 2), mask: masked}))];
      }), "Synthetic store features and alternative imputations")
    + table(["Reference", ...methods.map(method => methodLabel[method])],
      [[cluster(row.benchmark), ...methods.map(method => cluster(d.assignments[method][i]))]], "Aligned cluster assignments");
  }
  $("#discordance-only").addEventListener("change", drawPlot);
  $("#store-id").addEventListener("change", detail);
  drawPlot();
  detail();
  root.setAttribute("aria-busy", "false");
}

function loadNear(anchor, target, action) {
  const starting = document.querySelector(anchor);
  const observer = new IntersectionObserver(entries => {
    if (!entries.some(entry => entry.isIntersecting)) return;
    observer.disconnect();
    action().catch(error => {
      $(target).textContent = error.message;
      $(target).setAttribute("aria-busy", "false");
    });
  }, {rootMargin: "350px"});
  observer.observe(starting);
}

async function initialize() {
  initNavigation();
  loadNear("#demo", "#demo", demonstration);
  loadNear("#uncertainty-content", "#uncertainty-content", uncertainty);
  const study = await get("study");
  summaries(study);
  const go = labs(study);
  heatmap(study, go);
  sampleChart(study);
  pairedPanel(study);
  loadNear("#validation-scatter", "#validation-scatter", () => validationScatter(go, study));
}
initialize().catch(error => { $("#study-status").textContent = error.message; });
