import { beforeEach, describe, expect, it, vi } from "vitest";

import { handleMediaShortcut } from "./useMediaShortcuts";
import type { MediaShortcutActions } from "./useMediaShortcuts";

function makeActions(): MediaShortcutActions {
    return {
        togglePlay: vi.fn(),
        seekBackward: vi.fn(),
        seekForward: vi.fn(),
        toggleMute: vi.fn(),
        toggleFullscreen: vi.fn(),
        increaseVolume: vi.fn(),
        decreaseVolume: vi.fn(),
        increasePlaybackRate: vi.fn(),
        decreasePlaybackRate: vi.fn(),
    };
}

function dispatch(
    element: EventTarget,
    key: string,
    init: KeyboardEventInit = {},
): KeyboardEvent {
    const event = new KeyboardEvent("keydown", {
        key,
        bubbles: true,
        ...init,
    });
    element.dispatchEvent(event);
    return event;
}

describe("handleMediaShortcut", () => {
    let actions: MediaShortcutActions;

    beforeEach(() => {
        actions = makeActions();
        document.body.innerHTML = "";
    });

    it.each([
        [" ", "togglePlay"],
        ["p", "togglePlay"],
        ["m", "toggleMute"],
        ["f", "toggleFullscreen"],
        ["ArrowLeft", "seekBackward"],
        ["ArrowRight", "seekForward"],
        ["<", "decreasePlaybackRate"],
        [">", "increasePlaybackRate"],
    ] as const)("maps %j to %s", (key, action) => {
        const event = dispatch(document.body, key);
        expect(handleMediaShortcut(event, actions)).toBe(true);
        expect(actions[action]).toHaveBeenCalledOnce();
    });

    it.each([
        ["ArrowUp", "increaseVolume"],
        ["ArrowDown", "decreaseVolume"],
    ] as const)("maps shift+%s to %s", (key, action) => {
        const event = dispatch(document.body, key, { shiftKey: true });
        expect(handleMediaShortcut(event, actions)).toBe(true);
        expect(actions[action]).toHaveBeenCalledOnce();
    });

    it("leaves plain up/down arrows alone for page scrolling", () => {
        for (const key of ["ArrowUp", "ArrowDown"]) {
            const event = dispatch(document.body, key);
            expect(handleMediaShortcut(event, actions)).toBe(false);
        }
        expect(actions.increaseVolume).not.toHaveBeenCalled();
        expect(actions.decreaseVolume).not.toHaveBeenCalled();
    });

    it("ignores unmapped keys", () => {
        const event = dispatch(document.body, "x");
        expect(handleMediaShortcut(event, actions)).toBe(false);
    });

    it.each([
        ["ctrlKey"],
        ["metaKey"],
        ["altKey"],
    ] as const)("ignores shortcuts with %s held", (modifier) => {
        const event = dispatch(document.body, "p", { [modifier]: true });
        expect(handleMediaShortcut(event, actions)).toBe(false);
        expect(actions.togglePlay).not.toHaveBeenCalled();
    });

    it.each([
        ["input", "<input type='text' />"],
        ["textarea", "<textarea></textarea>"],
        ["select", "<select></select>"],
        ["button", "<button type='button'></button>"],
        ["contenteditable", "<div contenteditable='true'></div>"],
        ["media element", "<video></video>"],
        ["waveform", "<div id='waveform' tabindex='0'></div>"],
    ])("ignores keys originating from %s", (_label, html) => {
        document.body.innerHTML = html;
        const event = dispatch(document.body.firstElementChild!, " ");
        expect(handleMediaShortcut(event, actions)).toBe(false);
        expect(actions.togglePlay).not.toHaveBeenCalled();
    });

    it("ignores keys from children of self-handling elements", () => {
        document.body.innerHTML = "<button type='button'><svg></svg></button>";
        const svg = document.querySelector("svg")!;
        const event = dispatch(svg, " ");
        expect(handleMediaShortcut(event, actions)).toBe(false);
    });
});
