import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

/**
 * Manager payroll acceptance: employee-first calendar review plus weekly quick entry stays usable
 * across 375/768/1280 and at 200% zoom with an honest empty history, keyboard focus,
 * no horizontal overflow, and zero serious/critical axe violations.
 */

const CONSOLE = "/tests/e2e/fixtures/manager-console-empty.html";

const VIEWPORTS = [
  { name: "sm-375", width: 375, height: 720 },
  { name: "md-768", width: 768, height: 1024 },
  { name: "lg-1280", width: 1280, height: 800 },
];

test("keeps the empty worklog honest without fabricated rows", async ({ page }) => {
  await page.goto(CONSOLE);
  await expect(page.locator("[data-attendance-row]")).toHaveCount(0);
  await expect(page.locator("[data-attendance-empty]")).toHaveCount(1);
  await expect(page.locator("[data-attendance-empty]")).toContainText(
    "아직 입력된 시간이 없습니다.",
  );
  await expect(page.locator("body")).not.toContainText("EMP-0001");
});

test("offers a full monthly calendar and seven-row weekly quick entry", async ({ page }) => {
  await page.goto(CONSOLE);
  await expect(page.locator('select[name="employee"]')).toHaveCount(1);
  await expect(page.locator("[data-calendar-day]")).toHaveCount(31);
  await expect(page.getByRole("heading", { name: "월 근무 달력" })).toBeVisible();
  await expect(page.locator("[data-week-entry-row]")).toHaveCount(7);
  await expect(page.getByRole("button", { name: "이번 주 저장" })).toBeVisible();
});

test("calendar day jumps to quick entry", async ({ page }) => {
  await page.goto(CONSOLE);
  await page.locator('[data-calendar-day="2026-07-06"]').click();
  await expect(page.locator("#quick-entry")).toBeVisible();
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

    test("no horizontal overflow with calendar and weekly entry", async ({ page }) => {
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
