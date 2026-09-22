import { onBeforeUnmount, onMounted } from "vue";

export interface MediaShortcutActions {
    togglePlay(): void;
    seekBackward(): void;
    seekForward(): void;
    toggleMute(): void;
    toggleFullscreen(): void;
    increaseVolume(): void;
    decreaseVolume(): void;
    increasePlaybackRate(): void;
    decreasePlaybackRate(): void;
    jumpToPlayback(): void;
}

// Elements that handle keyboard input themselves. Which keys such an element
// consumes depends on the element, so a shortcut is only suppressed for the
// keys the element actually uses: a text field uses every key, a button only
// Space and Enter, and the waveform container only Space and the left and
// right arrows for its own fine-grained 0.5s seeking.
const SELF_HANDLING_SELECTOR =
    "input, textarea, select, button, [contenteditable], audio, video, #waveform";

const ALL_KEYS = "all";
const ACTIVATION_KEYS = [" ", "Enter"];
const ARROW_KEYS = ["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"];
const WAVEFORM_KEYS = [" ", "ArrowLeft", "ArrowRight"];

// Input types that are activated with Space or Enter instead of taking text.
const ACTIVATION_INPUT_TYPES = [
    "button",
    "checkbox",
    "color",
    "file",
    "image",
    "radio",
    "reset",
    "submit",
];

function keysHandledBy(element: HTMLElement): string[] | typeof ALL_KEYS {
    if (element.id === "waveform") {
        return WAVEFORM_KEYS;
    }
    const tagName = element.tagName.toLowerCase();
    if (tagName === "button") {
        return ACTIVATION_KEYS;
    }
    if (tagName === "input") {
        const type = (element as HTMLInputElement).type;
        if (ACTIVATION_INPUT_TYPES.includes(type)) {
            return ACTIVATION_KEYS;
        }
        if (type === "range") {
            return ARROW_KEYS;
        }
    }
    return ALL_KEYS;
}

function targetHandlesKey(target: HTMLElement | null, key: string): boolean {
    const element = target?.closest?.(SELF_HANDLING_SELECTOR) as
        | HTMLElement
        | null
        | undefined;
    if (!element) {
        return false;
    }
    const keys = keysHandledBy(element);
    return keys === ALL_KEYS || keys.includes(key);
}

export function handleMediaShortcut(
    event: KeyboardEvent,
    actions: MediaShortcutActions,
): boolean {
    if (event.ctrlKey || event.metaKey || event.altKey || event.isComposing) {
        return false;
    }
    if (targetHandlesKey(event.target as HTMLElement | null, event.key)) {
        return false;
    }

    switch (event.key) {
        case " ":
        case "p":
            actions.togglePlay();
            return true;
        case "ArrowLeft":
            if (event.shiftKey) return false;
            actions.seekBackward();
            return true;
        case "ArrowRight":
            if (event.shiftKey) return false;
            actions.seekForward();
            return true;
        case "ArrowUp":
            if (!event.shiftKey) return false;
            actions.increaseVolume();
            return true;
        case "ArrowDown":
            if (!event.shiftKey) return false;
            actions.decreaseVolume();
            return true;
        case "m":
            actions.toggleMute();
            return true;
        case "f":
            actions.toggleFullscreen();
            return true;
        case "<":
            actions.decreasePlaybackRate();
            return true;
        case ">":
            actions.increasePlaybackRate();
            return true;
        case "j":
            actions.jumpToPlayback();
            return true;
        default:
            return false;
    }
}

export function useMediaShortcuts(actions: MediaShortcutActions) {
    function onKeydown(event: KeyboardEvent) {
        if (handleMediaShortcut(event, actions)) {
            event.preventDefault();
        }
    }

    onMounted(() => window.addEventListener("keydown", onKeydown));
    onBeforeUnmount(() => window.removeEventListener("keydown", onKeydown));
}
