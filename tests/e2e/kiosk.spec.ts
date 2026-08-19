import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

/**
 * Kiosk UI acceptance: one state visible at a time, oversized targets, no web
 * storage, and — after a success auto-lock — no PIN or name left in the DOM.
 */

const KIOSK = "/tests/e2e/fixtures/kiosk.html";

const VIEWPORTS = [
  { name: "sm-375", width: 375, height: 720 },
  { name: "md-768", width: 768, height: 1024 },
  { name: "lg-1280", width: 1280, height: 800 },
];

test.beforeEach(async ({ page }) => {
  await page.route("**/kiosk/unlock/", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ ok: true, employee_name: "E2E 직원", shift_state: "WORKING" }),
    });
  });
  await page.route("**/kiosk/punch/", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ ok: true, kind: "CLOCK_OUT" }),
    });
  });
});

async function unlockWorking(page: import("@playwright/test").Page): Promise<void> {
  await page.getByRole("button", { name: "기록 시작" }).click();
  await page.locator('input[name="employee_code"]').fill("EMP-E2E");
  await page.locator("[data-pin]").fill("123456");
  await page.getByRole("button", { name: "확인" }).click();
}

async function visibleState(page: import("@playwright/test").Page): Promise<string | null> {
  return page.evaluate(() => {
    const shown = Array.from(document.querySelectorAll<HTMLElement>(".pb-kiosk__state")).filter(
      (el) => !el.hidden,
    );
    return shown.length === 1 ? (shown[0].dataset.state ?? null) : `count=${shown.length}`;
  });
}

test("starts locked with exactly one state visible", async ({ page }) => {
  await page.goto(KIOSK);
  expect(await visibleState(page)).toBe("locked");
});

test("uses no web storage at any point", async ({ page }) => {
  await page.goto(KIOSK);
  await page.getByRole("button", { name: "기록 시작" }).click();
  await page.locator('input[name="employee_code"]').fill("EMP-E2E");
  await page.locator("[data-pin]").fill("123456");
  const storage = await page.evaluate(() => ({
    local: localStorage.length,
    session: sessionStorage.length,
  }));
  expect(storage).toEqual({ local: 0, session: 0 });
});

test("success auto-locks and clears PIN and name", async ({ page }) => {
  await page.goto(KIOSK);
  await unlockWorking(page);
  await page.getByRole("button", { name: "퇴근" }).click();
  await expect(page.locator('.pb-kiosk__state[data-state="success"]')).toBeVisible();
  expect(await visibleState(page)).toBe("success");

  // Auto-lock within ~3s.
  await page.waitForTimeout(3500);
  expect(await visibleState(page)).toBe("locked");

  // Nothing sensitive survives.
  const pinValue = await page.locator("[data-pin]").inputValue();
  expect(pinValue).toBe("");
  const nameText = await page.evaluate(() =>
    Array.from(document.querySelectorAll("[data-employee-name]"))
      .map((n) => n.textContent?.trim())
      .join(""),
  );
  expect(nameText).toBe("");
});

for (const vp of VIEWPORTS) {
  test.describe(`viewport ${vp.name}`, () => {
    test.use({ viewport: { width: vp.width, height: vp.height } });

    test("no overflow and no serious axe violations on key states", async ({ page }) => {
      await page.goto(KIOSK);
      const assertPage = async () => {
        const overflow = await page.evaluate(
          () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
        );
        expect(overflow).toBeLessThanOrEqual(1);
        const results = await new AxeBuilder({ page }).analyze();
        const blocking = results.violations.filter(
          (v) => v.impact === "serious" || v.impact === "critical",
        );
        expect(blocking, JSON.stringify(blocking, null, 2)).toEqual([]);
      };
      await assertPage();
      await page.getByRole("button", { name: "기록 시작" }).click();
      await assertPage();
      await page.locator('input[name="employee_code"]').fill("EMP-E2E");
      await page.locator("[data-pin]").fill("123456");
      await page.getByRole("button", { name: "확인" }).click();
      await assertPage();
    });

    test("touch targets in the PIN state are >= 44x44", async ({ page }) => {
      await page.goto(KIOSK);
      await page.getByRole("button", { name: "기록 시작" }).click();
      const targets = page.locator(
        '.pb-kiosk__state[data-state="pin"] .pb-btn, .pb-kiosk__state[data-state="pin"] input:not([type="hidden"])',
      );
      const count = await targets.count();
      expect(count).toBeGreaterThan(0);
      for (let i = 0; i < count; i++) {
        const box = await targets.nth(i).boundingBox();
        expect(box).not.toBeNull();
        if (box) {
          expect(box.width).toBeGreaterThanOrEqual(44);
          expect(box.height).toBeGreaterThanOrEqual(44);
        }
      }
    });
  });
}
