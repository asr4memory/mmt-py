import { onBeforeUnmount, onMounted, readonly, ref } from "vue";

// Keys that scroll the page. Shift with the vertical arrows changes the
// volume instead, see useMediaShortcuts.
const SCROLL_KEYS = ["PageUp", "PageDown", "Home", "End"];
const ARROW_SCROLL_KEYS = ["ArrowUp", "ArrowDown"];

const TEXT_ENTRY_SELECTOR =
    "input:not([type=button], [type=checkbox], [type=radio], [type=range]), textarea, select, [contenteditable]";

function isTextEntry(target: EventTarget | null): boolean {
    return (
        target instanceof Element &&
        target.closest(TEXT_ENTRY_SELECTOR) !== null
    );
}

// Whether an element between the target and the document scrolls vertically
// itself. A wheel or touch gesture over it scrolls that element, not the page.
function insideScrollContainer(target: EventTarget | null): boolean {
    let element = target instanceof Element ? target : null;
    while (element && element !== document.documentElement) {
        const overflowY = getComputedStyle(element).overflowY;
        if (
            (overflowY === "auto" || overflowY === "scroll") &&
            element.scrollHeight > element.clientHeight
        ) {
            return true;
        }
        element = element.parentElement;
    }
    return false;
}

// Keeps the transcript scrolled to the playback position until the user
// scrolls. The scrolling done while following uses
// scrollIntoView, which fires the same scroll events as a user scroll, so
// following is stopped by the input events that only the user produces.
export function usePlaybackFollow(scrollToCurrent: () => void) {
    const following = ref(false);

    function start() {
        following.value = true;
        scrollToCurrent();
    }

    function stop() {
        following.value = false;
    }

    function toggle() {
        if (following.value) {
            stop();
        } else {
            start();
        }
    }

    // The check for a scroll container reads computed styles, so it is
    // skipped while the playback is not followed.
    function onScrollGesture(event: Event) {
        if (following.value && !insideScrollContainer(event.target)) {
            stop();
        }
    }

    function onKeydown(event: KeyboardEvent) {
        if (isTextEntry(event.target)) {
            return;
        }
        if (
            SCROLL_KEYS.includes(event.key) ||
            (ARROW_SCROLL_KEYS.includes(event.key) && !event.shiftKey)
        ) {
            stop();
        }
    }

    onMounted(() => {
        window.addEventListener("wheel", onScrollGesture, { passive: true });
        window.addEventListener("touchmove", onScrollGesture, {
            passive: true,
        });
        window.addEventListener("keydown", onKeydown);
    });

    onBeforeUnmount(() => {
        window.removeEventListener("wheel", onScrollGesture);
        window.removeEventListener("touchmove", onScrollGesture);
        window.removeEventListener("keydown", onKeydown);
    });

    return { following: readonly(following), start, stop, toggle };
}
