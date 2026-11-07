import { mount } from "@vue/test-utils";
import { describe, expect, test } from "vitest";
import { createI18n } from "vue-i18n";
import de from "../locales/de";
import TranscriptEndMark from "./transcript_end_mark.vue";
import type { TranscriptSegment } from "./types";

function segment(id: string, start: number, end: number): TranscriptSegment {
    return { id, start, end, speakerId: null, words: [] };
}

function mountEndMark(segments: TranscriptSegment[]) {
    const i18n = createI18n({
        legacy: false,
        locale: "de",
        messages: { de },
    });
    return mount(TranscriptEndMark, {
        props: { segments },
        global: { plugins: [i18n] },
    });
}

describe("TranscriptEndMark", () => {
    test("states the end time of the last segment", () => {
        const wrapper = mountEndMark([
            segment("s1", 0, 100),
            segment("s2", 100, 233.7),
        ]);

        expect(wrapper.find("p").text()).toBe("Ende des Transkripts · 0:03:53");
    });

    test("states a duration of zero for a transcript without segments", () => {
        const wrapper = mountEndMark([]);

        expect(wrapper.find("p").text()).toBe("Ende des Transkripts · 0:00:00");
    });
});
