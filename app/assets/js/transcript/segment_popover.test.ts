import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, test, vi } from "vitest";
import { ref } from "vue";
import SegmentPopover from "./segment_popover.vue";
import { useTranscriptStore } from "./transcript_store";
import type { TranscriptSegment } from "./types";

// Floating UI computes real layout, which jsdom cannot provide; the component's
// behavior is independent of where the popover ends up on screen.
vi.mock("@floating-ui/vue", () => ({
    useFloating: () => ({ floatingStyles: ref({}) }),
    autoUpdate: () => () => {},
    offset: () => ({}),
    flip: () => ({}),
    shift: () => ({}),
}));

function segment(id: string, start: number, end: number): TranscriptSegment {
    return {
        id,
        start,
        end,
        speakerId: null,
        words: [
            {
                id: `${id}_w1`,
                start,
                end,
                word: "hello",
                score: 1,
                speakerId: null,
            },
        ],
    };
}

function mountPopover(segmentId: string) {
    const store = useTranscriptStore();
    store.segments = [segment("seg_1", 0, 2), segment("seg_2", 2, 5)];
    const wrapper = mount(SegmentPopover, {
        props: {
            segment: store.segments.find((s) => s.id === segmentId)!,
            reference: document.createElement("span"),
        },
        global: {
            mocks: { $t: (key: string) => key },
            stubs: { teleport: true },
        },
    });
    return { wrapper, store };
}

function mergeButton(wrapper: ReturnType<typeof mountPopover>["wrapper"]) {
    return wrapper
        .findAll("button")
        .find((button) => button.attributes("title") === "merge_segment_up")!;
}

beforeEach(() => {
    setActivePinia(createPinia());
});

describe("SegmentPopover", () => {
    test("renders the merge action", () => {
        const { wrapper } = mountPopover("seg_2");

        expect(mergeButton(wrapper).exists()).toBe(true);
    });

    test("merges the segment into the previous one and closes", async () => {
        const { wrapper, store } = mountPopover("seg_2");

        await mergeButton(wrapper).trigger("click");

        expect(store.segments).toHaveLength(1);
        expect(store.segments[0].id).toBe("seg_1");
        expect(wrapper.emitted("close")).toHaveLength(1);
    });

    test("disables the merge action for the first segment", () => {
        const { wrapper } = mountPopover("seg_1");

        expect(mergeButton(wrapper).attributes("disabled")).toBeDefined();
    });

    test("enables the merge action for a later segment", () => {
        const { wrapper } = mountPopover("seg_2");

        expect(mergeButton(wrapper).attributes("disabled")).toBeUndefined();
    });
});
