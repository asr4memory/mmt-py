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
}

// Elements that handle keyboard input themselves. The waveform container
// keeps its own focused handlers for fine-grained 0.5s seeking.
const SELF_HANDLING_SELECTOR =
    "input, textarea, select, button, [contenteditable], audio, video, #waveform";

export function handleMediaShortcut(
    event: KeyboardEvent,
    actions: MediaShortcutActions,
): boolean {
    if (event.ctrlKey || event.metaKey || event.altKey || event.isComposing) {
        return false;
    }
    const target = event.target as HTMLElement | null;
    if (target?.closest?.(SELF_HANDLING_SELECTOR)) {
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
