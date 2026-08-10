import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

/**
 * Manager console acceptance: the fixed-sidenav / scroll-body shell stays usable
 * across 375/768/1280 and at 200% zoom with an honest empty table, keyboard focus, no
 * horizontal overflow, and zero serious/critical axe violations. Sensitive actions
 * require a typed reason.
 */

const CONSOLE = "/tests/e2e/fixtures/manager-console-empty.html";

const VIEWPORTS = [
  { name: "sm-375", width: 375, height: 720 },
  { name: "md-768", width: 768, height: 1024 },
  { name: "lg-1280", width: 1280, height: 800 },
];

test("keeps the empty attendance fixture honest without fabricated rows", async ({ page }) => {
  await page.goto(CONSOLE);
  await expect(page.locator("[data-attendance-row]")).toHaveCount(0);
  await expect(page.locator("[data-attendance-empty]")).toHaveCount(1);
  await expect(page.locator("[data-attendance-empty]")).toContainText(
    "표시할 실시간 근태 기록이 없습니다.",
  );
  await expect(page.locator("body")).not.toContainText("EMP-0001");
});

test("reopen requires a typed reason", async ({ page }) => {
  await page.goto(CONSOLE);
  await page.getByRole("button", { name: "재오픈" }).click();
  const submit = page.locator("#reopen-dialog [data-submit]");
  await expect(submit).toBeDisabled();
  await page.locator("#reopen-dialog [data-reason]").fill("시급 정정");
  await expect(submit).toBeEnabled();
});

for (const vp of VIEWPORTS) {
  test.describe(`viewport ${vp.name}`, () => {
    test.use({ viewport: { width: vp.width, height: vp.height } });

    test("no horizontal overflow with the attendance table", async ({ page }) => {
      await page.goto(CONSOLE);
      await page.locator("[data-attendance-empty]").waitFor();
      const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
      );
      expect(overflow).toBeLessThanOrEqual(1);
    });

    test("no serious or critical axe violations", async ({ page }) => {
      await page.goto(CONSOLE);
      await page.locator("[data-attendance-empty]").waitFor();
      const results = await new AxeBuilder({ page }).analyze();
      const blocking = results.violations.filter(
        (v) => v.impact === "serious" || v.impact === "critical",
      );
      expect(blocking, JSON.stringify(blocking, null, 2)).toEqual([]);
    });

    test("keyboard focus is visible on nav", async ({ page }) => {
      await page.goto(CONSOLE);
      await page.keyboard.press("Tab");
      const outline = await page.evaluate(() => {
        const el = document.activeElement as HTMLElement | null;
        return el ? getComputedStyle(el).outlineWidth : "0px";
      });
      expect(outline).not.toBe("0px");
    });
  });
}

test("survives 200% zoom without overflow", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.goto(CONSOLE);
  await page.evaluate(() => {
    (document.body.style as CSSStyleDeclaration & { zoom: string }).zoom = "2";
  });
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  );
  expect(overflow).toBeLessThanOrEqual(1);
});
