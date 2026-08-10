const AUTO_LOCK_MS = 3000;

type ScreenName = "locked" | "pin" | "action" | "success";
type ShiftState = "IDLE" | "WORKING" | "ON_BREAK";
type PunchKind = "CLOCK_IN" | "BREAK_START" | "BREAK_END" | "CLOCK_OUT";

type UnlockPayload = {
  readonly ok: true;
  readonly employee_name: string;
  readonly shift_state: ShiftState;
};

type PunchPayload = {
  readonly ok: true;
  readonly kind: PunchKind;
};

function isShiftState(value: unknown): value is ShiftState {
  return value === "IDLE" || value === "WORKING" || value === "ON_BREAK";
}

function isUnlockPayload(value: unknown): value is UnlockPayload {
  return (
    typeof value === "object" &&
    value !== null &&
    "ok" in value &&
    value.ok === true &&
    "employee_name" in value &&
    typeof value.employee_name === "string" &&
    "shift_state" in value &&
    isShiftState(value.shift_state)
  );
}

function isPunchPayload(value: unknown): value is PunchPayload {
  return (
    typeof value === "object" &&
    value !== null &&
    "ok" in value &&
    value.ok === true &&
    "kind" in value &&
    typeof value.kind === "string"
  );
}

function responseError(value: unknown, fallback: string): string {
  if (
    typeof value === "object" &&
    value !== null &&
    "error" in value &&
    typeof value.error === "string"
  ) {
    return value.error;
  }
  return fallback;
}

function announce(message: string): void {
  const live = document.querySelector<HTMLElement>("[data-live]");
  if (live) live.textContent = message;
}

function show(screen: ScreenName): void {
  for (const element of document.querySelectorAll<HTMLElement>(".pb-kiosk__state")) {
    element.hidden = element.dataset.state !== screen;
  }
  const active = document.querySelector<HTMLElement>(`.pb-kiosk__state[data-state="${screen}"]`);
  if (!active) return;
  announce(active.dataset.announce ?? "");
  active.querySelector<HTMLElement>("input, button")?.focus();
}

function clearSensitive(): void {
  for (const input of document.querySelectorAll<HTMLInputElement>(
    'input[name="employee_code"], [data-pin]',
  )) {
    input.value = "";
  }
  for (const name of document.querySelectorAll<HTMLElement>("[data-employee-name]")) {
    name.textContent = "";
  }
}

function lock(): void {
  clearSensitive();
  const error = document.querySelector<HTMLElement>("[data-kiosk-error]");
  if (error) error.textContent = "";
  show("locked");
}

function idempotencyKey(): string {
  return (crypto.randomUUID?.() ?? `${Date.now()}-${Math.random()}`).replace(/[^a-z0-9-]/gi, "");
}

function csrfToken(): string {
  return document.querySelector<HTMLInputElement>('input[name="csrfmiddlewaretoken"]')?.value ?? "";
}

function syncActions(state: ShiftState): void {
  const allowed: readonly PunchKind[] =
    state === "IDLE"
      ? ["CLOCK_IN"]
      : state === "WORKING"
        ? ["BREAK_START", "CLOCK_OUT"]
        : ["BREAK_END"];
  for (const button of document.querySelectorAll<HTMLButtonElement>("[data-punch]")) {
    const kind = button.dataset.punch;
    button.hidden = !allowed.some((value) => value === kind);
  }
  const label = document.querySelector<HTMLElement>("[data-shift-state]");
  if (label) {
    label.textContent = state === "IDLE" ? "출근 전" : state === "WORKING" ? "근무 중" : "휴게 중";
  }
}

async function unlock(form: HTMLFormElement): Promise<void> {
  const error = form.querySelector<HTMLElement>("[data-kiosk-error]");
  if (error) error.textContent = "";
  try {
    const response = await fetch("/kiosk/unlock/", { method: "POST", body: new FormData(form) });
    const payload: unknown = await response.json();
    if (!response.ok || !isUnlockPayload(payload)) {
      if (error) error.textContent = responseError(payload, "직원 코드와 PIN을 확인해주세요.");
      return;
    }
    for (const name of document.querySelectorAll<HTMLElement>("[data-employee-name]")) {
      name.textContent = payload.employee_name;
    }
    syncActions(payload.shift_state);
    show("action");
  } catch (errorValue) {
    if (errorValue instanceof TypeError) {
      if (error) error.textContent = "서버에 연결할 수 없습니다. 잠시 후 다시 시도해주세요.";
      return;
    }
    throw errorValue;
  }
}

async function punch(kind: PunchKind): Promise<void> {
  const body = new FormData();
  body.set("csrfmiddlewaretoken", csrfToken());
  body.set("kind", kind);
  body.set("idempotency_key", idempotencyKey());
  const response = await fetch("/kiosk/punch/", { method: "POST", body });
  const payload: unknown = await response.json();
  if (!response.ok || !isPunchPayload(payload)) {
    announce(responseError(payload, "근무 기록을 저장하지 못했습니다."));
    show("pin");
    return;
  }
  const result = document.querySelector<HTMLElement>("[data-punch-result]");
  if (result) {
    const labels: Record<PunchKind, string> = {
      CLOCK_IN: "출근이 기록되었습니다",
      BREAK_START: "휴게 시작이 기록되었습니다",
      BREAK_END: "휴게 종료가 기록되었습니다",
      CLOCK_OUT: "퇴근이 기록되었습니다",
    };
    result.textContent = labels[payload.kind];
  }
  show("success");
  window.setTimeout(lock, AUTO_LOCK_MS);
}

function wire(): void {
  document
    .querySelector<HTMLButtonElement>("[data-start]")
    ?.addEventListener("click", () => show("pin"));
  for (const button of document.querySelectorAll<HTMLButtonElement>("[data-lock]")) {
    button.addEventListener("click", lock);
  }
  document
    .querySelector<HTMLFormElement>("[data-unlock-form]")
    ?.addEventListener("submit", (event) => {
      event.preventDefault();
      const form = event.currentTarget;
      if (form instanceof HTMLFormElement) void unlock(form);
    });
  for (const button of document.querySelectorAll<HTMLButtonElement>("[data-punch]")) {
    button.addEventListener("click", () => {
      const kind = button.dataset.punch;
      if (
        kind === "CLOCK_IN" ||
        kind === "BREAK_START" ||
        kind === "BREAK_END" ||
        kind === "CLOCK_OUT"
      ) {
        void punch(kind);
      }
    });
  }
  lock();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", wire);
} else {
  wire();
}

export {};
