import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

/**
 * Design-system acceptance for four personas:
 *  1) 바쁜 공유-태블릿 직원  2) 월마감 점장
 *  3) 저시력/키보드 사용자    4) 한 손 사용 제약 사용자
 *
 * Verifies, across 375/768/1280 and at 200% zoom: zero horizontal overflow,
 * visible keyboard focus, ≥44×44 touch targets, and no serious/critical axe
 * violations.
 */

const SHOWCASE = "/templates/design-system/showcase.html";

const VIEWPORTS = [
  { name: "sm-375", width: 375, height: 720 },
  { name: "md-768", width: 768, height: 1024 },
  { name: "lg-1280", width: 1280, height: 800 },
];

const TARGET_SELECTOR = ".pb-btn, .pb-input, .pb-shell__nav a";

test("names the four personas", async ({ page }) => {
  await page.goto(SHOWCASE);
  for (const persona of [
    "바쁜 공유-태블릿 직원",
    "월마감 점장",
    "저시력/키보드 사용자",
    "한 손 사용 제약 사용자",
  ]) {
    await expect(page.getByText(persona)).toBeVisible();
  }
});

for (const vp of VIEWPORTS) {
  test.describe(`viewport ${vp.name}`, () => {
    test.use({ viewport: { width: vp.width, height: vp.height } });

    test("no horizontal overflow", async ({ page }) => {
      await page.goto(SHOWCASE);
      const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
      );
      expect(overflow).toBeLessThanOrEqual(1);
    });

    test("touch targets are at least 44x44", async ({ page }) => {
      await page.goto(SHOWCASE);
      const targets = page.locator(TARGET_SELECTOR);
      const count = await targets.count();
      expect(count).toBeGreaterThan(0);
      for (let i = 0; i < count; i++) {
        const el = targets.nth(i);
        if (!(await el.isVisible())) continue;
        const box = await el.boundingBox();
        expect(box).not.toBeNull();
        if (box) {
          expect(box.width).toBeGreaterThanOrEqual(44);
          expect(box.height).toBeGreaterThanOrEqual(44);
        }
      }
    });

    test("keyboard focus is visible", async ({ page }) => {
      await page.goto(SHOWCASE);
      await page.keyboard.press("Tab");
      const outlineWidth = await page.evaluate(() => {
        const el = document.activeElement as HTMLElement | null;
        return el ? getComputedStyle(el).outlineWidth : "0px";
      });
      expect(outlineWidth).not.toBe("0px");
    });

    test("no serious or critical axe violations", async ({ page }) => {
      await page.goto(SHOWCASE);
      const results = await new AxeBuilder({ page }).analyze();
      const blocking = results.violations.filter(
        (v) => v.impact === "serious" || v.impact === "critical",
      );
      expect(blocking, JSON.stringify(blocking, null, 2)).toEqual([]);
    });
  });
}

test("survives 200% zoom without overflow or lost focus", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.goto(SHOWCASE);
  await page.evaluate(() => {
    (document.body.style as CSSStyleDeclaration & { zoom: string }).zoom = "2";
  });
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  );
  expect(overflow).toBeLessThanOrEqual(1);
  await page.keyboard.press("Tab");
  const outlineWidth = await page.evaluate(() => {
    const el = document.activeElement as HTMLElement | null;
    return el ? getComputedStyle(el).outlineWidth : "0px";
  });
  expect(outlineWidth).not.toBe("0px");
});
