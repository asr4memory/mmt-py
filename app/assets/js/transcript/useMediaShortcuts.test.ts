import { beforeEach, describe, expect, test, vi } from "vitest";

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
        jumpToPlayback: vi.fn(),
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

    test.each([
        [" ", "togglePlay"],
        ["p", "togglePlay"],
        ["m", "toggleMute"],
        ["f", "toggleFullscreen"],
        ["ArrowLeft", "seekBackward"],
        ["ArrowRight", "seekForward"],
        ["<", "decreasePlaybackRate"],
        [">", "increasePlaybackRate"],
        ["j", "jumpToPlayback"],
    ] as const)("maps %j to %s", (key, action) => {
        const event = dispatch(document.body, key);
        expect(handleMediaShortcut(event, actions)).toBe(true);
        expect(actions[action]).toHaveBeenCalledOnce();
    });

    test.each([
        ["ArrowUp", "increaseVolume"],
        ["ArrowDown", "decreaseVolume"],
    ] as const)("maps shift+%s to %s", (key, action) => {
        const event = dispatch(document.body, key, { shiftKey: true });
        expect(handleMediaShortcut(event, actions)).toBe(true);
        expect(actions[action]).toHaveBeenCalledOnce();
    });

    test("leaves plain up/down arrows alone for page scrolling", () => {
        for (const key of ["ArrowUp", "ArrowDown"]) {
            const event = dispatch(document.body, key);
            expect(handleMediaShortcut(event, actions)).toBe(false);
        }
        expect(actions.increaseVolume).not.toHaveBeenCalled();
        expect(actions.decreaseVolume).not.toHaveBeenCalled();
    });

    test("ignores unmapped keys", () => {
        const event = dispatch(document.body, "x");
        expect(handleMediaShortcut(event, actions)).toBe(false);
    });

    test.each([["ctrlKey"], ["metaKey"], ["altKey"]] as const)(
        "ignores shortcuts with %s held",
        (modifier) => {
            const event = dispatch(document.body, "p", { [modifier]: true });
            expect(handleMediaShortcut(event, actions)).toBe(false);
            expect(actions.togglePlay).not.toHaveBeenCalled();
        },
    );

    test.each([
        ["input", "<input type='text' />"],
        ["textarea", "<textarea></textarea>"],
        ["select", "<select></select>"],
        ["button", "<button type='button'></button>"],
        ["contenteditable", "<div contenteditable='true'></div>"],
        ["media element with controls", "<video controls></video>"],
        ["waveform", "<div id='waveform' tabindex='0'></div>"],
    ])("ignores keys originating from %s", (_label, html) => {
        document.body.innerHTML = html;
        const event = dispatch(document.body.firstElementChild!, " ");
        expect(handleMediaShortcut(event, actions)).toBe(false);
        expect(actions.togglePlay).not.toHaveBeenCalled();
    });

    test("ignores keys from children of self-handling elements", () => {
        document.body.innerHTML = "<button type='button'><svg></svg></button>";
        const svg = document.querySelector("svg")!;
        const event = dispatch(svg, " ");
        expect(handleMediaShortcut(event, actions)).toBe(false);
    });

    test.each([
        ["button", "<button type='button'></button>"],
        ["button input", "<input type='button' />"],
        ["checkbox", "<input type='checkbox' />"],
        ["range input", "<input type='range' />"],
    ])("runs letter shortcuts while %s has focus", (_label, html) => {
        document.body.innerHTML = html;
        const target = document.body.firstElementChild!;
        for (const key of ["p", "j", "m", "f"]) {
            const event = dispatch(target, key);
            expect(handleMediaShortcut(event, actions)).toBe(true);
        }
        expect(actions.togglePlay).toHaveBeenCalledOnce();
        expect(actions.jumpToPlayback).toHaveBeenCalledOnce();
        expect(actions.toggleMute).toHaveBeenCalledOnce();
        expect(actions.toggleFullscreen).toHaveBeenCalledOnce();
    });

    test.each([
        ["button", "<button type='button'></button>"],
        ["checkbox", "<input type='checkbox' />"],
    ])("leaves Space and Enter to a focused %s", (_label, html) => {
        document.body.innerHTML = html;
        const target = document.body.firstElementChild!;
        for (const key of [" ", "Enter"]) {
            const event = dispatch(target, key);
            expect(handleMediaShortcut(event, actions)).toBe(false);
        }
        expect(actions.togglePlay).not.toHaveBeenCalled();
    });

    test("leaves arrow keys to a focused range input", () => {
        document.body.innerHTML = "<input type='range' />";
        const target = document.body.firstElementChild!;
        for (const key of ["ArrowLeft", "ArrowRight"]) {
            const event = dispatch(target, key);
            expect(handleMediaShortcut(event, actions)).toBe(false);
        }
        expect(actions.seekBackward).not.toHaveBeenCalled();
        expect(actions.seekForward).not.toHaveBeenCalled();
    });

    test.each([
        ["text input", "<input type='text' />"],
        ["textarea", "<textarea></textarea>"],
        ["select", "<select></select>"],
        ["contenteditable", "<div contenteditable='true'></div>"],
    ])("ignores letter shortcuts from %s", (_label, html) => {
        document.body.innerHTML = html;
        const event = dispatch(document.body.firstElementChild!, "j");
        expect(handleMediaShortcut(event, actions)).toBe(false);
        expect(actions.jumpToPlayback).not.toHaveBeenCalled();
    });

    test.each([
        ["video", "<video></video>"],
        ["audio", "<audio></audio>"],
    ])(
        "runs every shortcut while a %s without controls has focus",
        (_label, html) => {
            document.body.innerHTML = html;
            const target = document.body.firstElementChild!;
            for (const key of [" ", "j", "p", "m", "ArrowLeft"]) {
                expect(
                    handleMediaShortcut(dispatch(target, key), actions),
                ).toBe(true);
            }
        },
    );

    test("runs only the shortcuts the native video controls do not use", () => {
        document.body.innerHTML = "<video controls></video>";
        const target = document.body.firstElementChild!;
        for (const key of [" ", "m", "f", "ArrowLeft", "ArrowRight"]) {
            expect(handleMediaShortcut(dispatch(target, key), actions)).toBe(
                false,
            );
        }
        for (const key of ["j", "p", "<", ">"]) {
            expect(handleMediaShortcut(dispatch(target, key), actions)).toBe(
                true,
            );
        }
    });

    test("runs only the shortcuts the waveform does not handle itself", () => {
        document.body.innerHTML = "<div id='waveform' tabindex='0'></div>";
        const target = document.body.firstElementChild!;
        for (const key of [" ", "ArrowLeft", "ArrowRight"]) {
            expect(handleMediaShortcut(dispatch(target, key), actions)).toBe(
                false,
            );
        }
        for (const key of ["p", "j", "m"]) {
            expect(handleMediaShortcut(dispatch(target, key), actions)).toBe(
                true,
            );
        }
    });
});
