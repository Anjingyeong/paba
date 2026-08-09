/**
 * Manager console client behaviour (progressive enhancement only).
 *
 * - marks the current sidenav item,
 * - gates sensitive actions behind a confirm dialog that requires a typed reason,
 * - keeps focus managed so it is never lost when a dialog opens/closes.
 *
 * No web storage is used.
 */

function wireConfirmDialogs(): void {
  for (const trigger of document.querySelectorAll<HTMLButtonElement>("[data-confirm]")) {
    const dialogId = trigger.dataset.confirm ?? "";
    const dialog = document.getElementById(dialogId) as HTMLDialogElement | null;
    if (!dialog) continue;

    trigger.addEventListener("click", () => {
      dialog.showModal();
      dialog.querySelector<HTMLElement>("input, textarea, button")?.focus();
    });

    const reason = dialog.querySelector<HTMLInputElement>("[data-reason]");
    const submit = dialog.querySelector<HTMLButtonElement>("[data-submit]");
    const cancel = dialog.querySelector<HTMLButtonElement>("[data-cancel]");

    const sync = () => {
      if (submit && reason) submit.disabled = reason.value.trim().length === 0;
    };
    reason?.addEventListener("input", sync);
    sync();

    cancel?.addEventListener("click", () => {
      dialog.close();
      trigger.focus();
    });
    submit?.addEventListener("click", () => {
      dialog.close();
      trigger.focus();
    });
  }
}

function fillBulkTable(): void {
  const body = document.querySelector<HTMLTableSectionElement>("[data-bulk-rows]");
  if (!body) return;
  const rows: string[] = [];
  for (let i = 1; i <= 100; i++) {
    const code = `EMP-${String(i).padStart(4, "0")}`;
    rows.push(
      `<tr><td data-label="직원">${code}</td>` +
        `<td data-label="지급시간">${(150 + (i % 40)).toFixed(2)}</td>` +
        `<td data-label="상태">${i % 7 === 0 ? "검토" : "승인"}</td></tr>`,
    );
  }
  body.innerHTML = rows.join("");
}

function wire(): void {
  wireConfirmDialogs();
  fillBulkTable();
  document.documentElement.dataset.pbManager = "ready";
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", wire);
} else {
  wire();
}

export {};
