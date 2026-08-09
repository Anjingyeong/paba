/**
 * Kiosk client behaviour: a small state machine that shows exactly one state at a
 * time, announces changes to screen readers, generates a per-action idempotency
 * key, auto-locks within 3 seconds of a success, and — critically — clears the PIN
 * and employee name from the DOM so nothing survives to the next person. It never
 * uses localStorage/sessionStorage.
 */

const AUTO_LOCK_MS = 3000;

type StateName = "locked" | "pin" | "action" | "break" | "success" | "correction" | "network-error";

function announce(message: string): void {
  const live = document.querySelector<HTMLElement>("[data-live]");
  if (live) live.textContent = message;
}

function show(state: StateName): void {
  const states = document.querySelectorAll<HTMLElement>(".pb-kiosk__state");
  for (const el of states) {
    el.hidden = el.dataset.state !== state;
  }
  const active = document.querySelector<HTMLElement>(`.pb-kiosk__state[data-state="${state}"]`);
  if (active) {
    announce(active.dataset.announce ?? "");
    const focusable = active.querySelector<HTMLElement>("input, button, [tabindex]");
    focusable?.focus();
  }
}

function clearSensitive(): void {
  for (const input of document.querySelectorAll<HTMLInputElement>("[data-pin]")) {
    input.value = "";
  }
  for (const name of document.querySelectorAll<HTMLElement>("[data-employee-name]")) {
    name.textContent = "";
  }
}

function lock(): void {
  clearSensitive();
  show("locked");
}

function newIdempotencyKey(): string {
  return (crypto.randomUUID?.() ?? `${Date.now()}-${Math.random()}`).replace(/[^a-z0-9-]/gi, "");
}

function wire(): void {
  document.body.dataset.idempotencyKey = newIdempotencyKey();

  for (const trigger of document.querySelectorAll<HTMLElement>("[data-go]")) {
    trigger.addEventListener("click", () => {
      const target = trigger.dataset.go as StateName;
      if (target === "success") {
        show("success");
        window.setTimeout(lock, AUTO_LOCK_MS);
      } else if (target === "locked") {
        lock();
      } else {
        show(target);
      }
    });
  }

  // Start locked; never persist anything to web storage.
  lock();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", wire);
} else {
  wire();
}

export {};
