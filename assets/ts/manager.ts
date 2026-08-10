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

function wireSectionNavigation(): void {
  const links = document.querySelectorAll<HTMLAnchorElement>(".pb-shell__nav-list a[href^='#']");

  const sync = (): void => {
    const target = window.location.hash || "#today";
    for (const link of links) {
      if (link.getAttribute("href") === target) {
        link.setAttribute("aria-current", "page");
      } else {
        link.removeAttribute("aria-current");
      }
    }
  };

  window.addEventListener("hashchange", sync);
  sync();
}

function wire(): void {
  wireSectionNavigation();
  wireConfirmDialogs();
  document.documentElement.dataset.pbManager = "ready";
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", wire);
} else {
  wire();
}

export {};
