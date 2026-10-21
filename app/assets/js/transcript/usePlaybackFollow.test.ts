import { mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { defineComponent, h } from "vue";
import { usePlaybackFollow } from "./usePlaybackFollow";

let scrollToCurrent: ReturnType<typeof vi.fn<() => void>>;
let follow: ReturnType<typeof usePlaybackFollow>;
let wrapper: ReturnType<typeof mount>;

// The host renders a text input and a transcript element with a nested
// element that can be made a scroll container.
const Host = defineComponent({
    setup() {
        follow = usePlaybackFollow(scrollToCurrent);
        return () =>
            h("div", [
                h("input", { id: "outside", type: "text" }),
                h("div", { id: "transcript" }, [
                    h("p", { id: "text" }, "Some words"),
                    h("div", { id: "nested" }, [h("p", { id: "inner" })]),
                ]),
            ]);
    },
});

function element(id: string): HTMLElement {
    return document.getElementById(id) as HTMLElement;
}

function keydown(target: EventTarget, key: string, init = {}) {
    target.dispatchEvent(
        new KeyboardEvent("keydown", { key, bubbles: true, ...init }),
    );
}

beforeEach(() => {
    scrollToCurrent = vi.fn<() => void>();
    wrapper = mount(Host, { attachTo: document.body });
    follow.start();
    scrollToCurrent.mockClear();
});

afterEach(() => {
    wrapper.unmount();
});

describe("usePlaybackFollow toggling", () => {
    test("scrolls to the current position when following starts", () => {
        follow.stop();

        follow.toggle();

        expect(follow.following.value).toBe(true);
        expect(scrollToCurrent).toHaveBeenCalledOnce();
    });

    test("stops following when toggled while following", () => {
        follow.toggle();

        expect(follow.following.value).toBe(false);
        expect(scrollToCurrent).not.toHaveBeenCalled();
    });
});

describe("usePlaybackFollow manual scrolling", () => {
    test.each([
        ["wheel", () => new WheelEvent("wheel", { bubbles: true })],
        ["touchmove", () => new Event("touchmove", { bubbles: true })],
    ])("stops following on %s over the transcript", (_name, makeEvent) => {
        element("text").dispatchEvent(makeEvent());

        expect(follow.following.value).toBe(false);
    });

    test("keeps following on wheel inside a nested scroll container", () => {
        const nested = element("nested");
        nested.style.overflowY = "auto";
        Object.defineProperty(nested, "scrollHeight", { value: 200 });
        Object.defineProperty(nested, "clientHeight", { value: 100 });

        element("inner").dispatchEvent(
            new WheelEvent("wheel", { bubbles: true }),
        );

        expect(follow.following.value).toBe(true);
    });

    test.each(["PageUp", "PageDown", "Home", "End", "ArrowUp", "ArrowDown"])(
        "stops following on %s",
        (key) => {
            keydown(document.body, key);

            expect(follow.following.value).toBe(false);
        },
    );

    test("keeps following on Shift+ArrowDown, which changes the volume", () => {
        keydown(document.body, "ArrowDown", { shiftKey: true });

        expect(follow.following.value).toBe(true);
    });

    test("keeps following on scroll keys typed into a text field", () => {
        keydown(element("outside"), "End");

        expect(follow.following.value).toBe(true);
    });
});
