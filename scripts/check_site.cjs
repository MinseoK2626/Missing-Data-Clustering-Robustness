/* Browser smoke tests for an assembled site. Requires the Playwright Node package. */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const { chromium } = require("playwright");

const url = process.env.BDV_SITE_URL || "http://127.0.0.1:8000/";
const screenshots = process.env.BDV_SCREENSHOTS;

async function main() {
  const browser = await chromium.launch({
    ...(process.env.BDV_CHROMIUM && { executablePath: process.env.BDV_CHROMIUM }),
    args: ["--no-sandbox"],
  });
  try {
    const desktop = await browser.newPage({viewport: {width: 1440, height: 1000}});
    const errors = [];
    desktop.on("pageerror", error => errors.push(error.message));
    desktop.on("console", message => {
      if (message.type() === "error") errors.push(message.text());
    });
    desktop.on("response", response => {
      if (response.status() >= 400) errors.push(`${response.status()} ${response.url()}`);
    });
    const shot = async (page, name, section) => {
      if (!screenshots) return;
      fs.mkdirSync(screenshots, { recursive: true });
      const path = `${screenshots}/${name}.png`;
      if (section) await page.locator(section).screenshot({path});
      else await page.screenshot({path});
    };
    await desktop.goto(url);
    await desktop.waitForFunction(() => document.querySelector("#study-status").textContent.includes("usable of"));
    assert.equal(await desktop.locator("#study-counts dd").first().textContent(), "4,800");
    await shot(desktop, "01-overview-desktop");
    for (const link of await desktop.locator("a[href^='#']").all()) {
      const anchor = await link.getAttribute("href");
      assert.equal(await desktop.locator(anchor).count(), 1, anchor);
    }
    const links = await desktop.locator("a").evaluateAll(elements => elements
      .filter(element => element.origin === location.origin && !element.hash)
      .map(element => element.href));
    for (const link of new Set(links)) {
      assert.ok((await desktop.request.head(link)).ok(), link);
    }

    await desktop.locator("#lab-mech").selectOption("MNAR");
    await desktop.locator("#lab-rate").selectOption("0.4");
    await desktop.locator("#lab-metric").selectOption("silhouette");
    await desktop.locator("#lab-controls input[value=zero]").uncheck();
    assert.equal(await desktop.getByRole("table", {name: "Selected metric and uncertainty"}).locator("tbody tr").count(), 3);
    await desktop.locator("#lab-view").selectOption("Individual seeds");
    await desktop.getByRole("table", {name: "Seed-level experimental results"}).waitFor();
    assert.equal(await desktop.getByRole("table", {name: "Seed-level experimental results"}).locator("tbody tr").count(), 240);
    await desktop.locator("#lab-reset").click();
    assert.equal(await desktop.locator("#lab-mech").inputValue(), "MCAR");
    await shot(desktop, "02-experiment-lab", "#lab");
    await desktop.locator("#design summary").click();
    assert.equal(await desktop.locator("[data-config]").count(), 60);
    await desktop.locator("[data-config]").last().click();
    assert.equal(await desktop.locator("#lab-mech").inputValue(), "MNAR");
    await desktop.locator("#design summary").click();
    await desktop.locator("#heat-metric").selectOption("change_rate");
    await desktop.locator("[data-heat]").first().click();
    assert.equal(await desktop.locator("#lab-metric").inputValue(), "change_rate");

    await desktop.locator("#methodology").scrollIntoViewIfNeeded();
    await desktop.locator("#demo").scrollIntoViewIfNeeded();
    await desktop.locator("#demo-mech").selectOption("MNAR");
    await desktop.locator("#demo-rate").selectOption("0.4");
    await desktop.locator("#demo-method").selectOption("knn");
    for (const stage of ["Complete values", "Missingness mask", "Observed values", "Imputed values", "Cluster assignments"]) {
      await desktop.locator("#demo-stage").selectOption(stage);
      assert.equal(await desktop.locator("#demo-result tbody tr").count(), 8);
    }
    await desktop.locator("#demo-stage").selectOption("Imputed values");
    assert.ok(await desktop.locator("#demo-result td.masked").count());
    await shot(desktop, "03-missingness-demonstration", ".figure-section");

    await desktop.locator("#validation-scatter").scrollIntoViewIfNeeded();
    await desktop.locator("#scatter-mech").selectOption("MAR");
    await desktop.locator("#scatter-method").selectOption("all");
    await desktop.locator("#scatter-highlight").check();
    assert.ok(await desktop.locator("#validation-scatter circle").count());
    await desktop.locator("#scatter-example").selectOption({index: 1});
    assert.match(await desktop.locator("#validation-scatter .chart-status").textContent(), /Seed/);
    await shot(desktop, "04-validation-results", "#finding-2");
    await desktop.locator("#scatter-open").click();
    assert.equal(await desktop.locator("#lab-mech").inputValue(), "MAR");
    await desktop.locator("#sample-mech").selectOption("MCAR");
    const before = await desktop.locator("#sample-chart circle").count();
    await desktop.locator("#sample-seeds").uncheck();
    assert.ok(await desktop.locator("#sample-chart circle").count() < before);
    await desktop.locator("#pair-mech").selectOption("MNAR");
    await desktop.locator("#pair-rate").selectOption("0.4");
    assert.equal(await desktop.getByRole("table", {name: "Paired comparison estimates"}).locator("tbody tr").count(), 6);

    await desktop.locator("#uncertainty-content").scrollIntoViewIfNeeded();
    await desktop.locator("#discordance-only").check();
    assert.equal(await desktop.locator("#uncertainty-plot circle").count(), 183);
    await desktop.locator("#store-id").selectOption({index: 5});
    assert.match(await desktop.locator("#store-detail").textContent(), /Cluster [1-4]/);
    await shot(desktop, "05-store-uncertainty", "#uncertainty");
    assert.deepEqual(errors, []);

    for (const [name, width, height] of [["tablet", 768, 1024], ["mobile", 390, 844]]) {
      const page = await browser.newPage({viewport: {width, height}, isMobile: name === "mobile", hasTouch: true});
      await page.goto(url);
      await page.waitForFunction(() => document.querySelector("#study-counts dd"));
      assert.ok(await page.evaluate(expected => document.documentElement.scrollWidth <= expected + 1, width));
      await shot(page, `06-overview-${name}`);
      await page.locator(".mobile-nav summary").click();
      await page.locator(".mobile-nav").getByRole("link", {name: "Experiment lab"}).click();
      assert.equal(new URL(page.url()).hash, "#lab");
      assert.equal(await page.locator(".mobile-nav").getAttribute("open"), null);
      await page.locator("#lab-mech").selectOption("MAR");
      assert.ok(await page.evaluate(expected => document.documentElement.scrollWidth <= expected + 1, width));
      await page.close();
    }
    console.log("Passed Chromium checks for controls, links and three viewport widths");
  } finally {
    await browser.close();
  }
}

main().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
