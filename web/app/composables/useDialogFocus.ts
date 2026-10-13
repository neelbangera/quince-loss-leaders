import type { Ref } from "vue";

const FOCUSABLE =
  'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

// Modal dialog behaviour: lock page scroll, move focus in, trap Tab, close on
// Escape, and return focus to whatever opened the dialog.
export function useDialogFocus(dialog: Ref<HTMLElement | null>, isOpen: Ref<boolean>, close: () => void) {
  let previouslyFocused: HTMLElement | null = null;

  function onKeydown(event: KeyboardEvent) {
    if (!isOpen.value) return;
    if (event.key === "Escape") {
      event.preventDefault();
      close();
      return;
    }
    if (event.key !== "Tab" || !dialog.value) return;
    const nodes = Array.from(dialog.value.querySelectorAll<HTMLElement>(FOCUSABLE))
      .filter((element) => element.offsetParent !== null);
    const first = nodes[0];
    const last = nodes[nodes.length - 1];
    if (!first || !last) return;
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }

  watch(isOpen, async (open) => {
    if (!import.meta.client) return;
    document.body.style.overflow = open ? "hidden" : "";
    if (open) {
      previouslyFocused = (document.activeElement as HTMLElement | null) ?? null;
      await nextTick();
      dialog.value?.querySelector<HTMLElement>(FOCUSABLE)?.focus();
    } else if (previouslyFocused) {
      previouslyFocused.focus();
      previouslyFocused = null;
    }
  });

  onMounted(() => document.addEventListener("keydown", onKeydown, true));
  onBeforeUnmount(() => {
    document.removeEventListener("keydown", onKeydown, true);
    document.body.style.overflow = "";
  });
}
