import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, test, vi } from "vitest";
import { nextTick } from "vue";

import Timecode from "./timecode.vue";
import { useTranscriptStore } from "./transcript_store";
import type { TranscriptSegment } from "./types";
import { WaveformRenderer } from "./waveform_renderer";
import WaveformComponent from "./waveform_component.vue";

vi.mock("./waveform_renderer", async (importOriginal) => {
    const original =
        await importOriginal<typeof import("./waveform_renderer")>();
    return {
        ...original,
        WaveformRenderer: vi.fn(function () {
            return {
                render: vi.fn(),
                updateTime: vi.fn(),
                updatePlayhead: vi.fn(),
                destroy: vi.fn(),
            };
        }),
    };
});

function segment(): TranscriptSegment {
    return {
        id: "seg_1",
        start: 0,
        end: 1,
        speakerId: "spk_1",
        words: [],
    };
}

async function mountWaveform(activeSegment: TranscriptSegment = segment()) {
    const store = useTranscriptStore();
    store.segments = [activeSegment];

    const wrapper = mount(WaveformComponent, {
        props: {
            transcriptId: 25,
            uploadedFileId: 166,
            activeSegmentIdx: 0,
            mediaElement: document.createElement("audio"),
        },
    });
    await flushPromises();

    const renderer = vi.mocked(WaveformRenderer).mock.results[0].value;
    return { wrapper, renderer };
}

describe("WaveformComponent", () => {
    beforeEach(() => {
        setActivePinia(createPinia());
        vi.mocked(WaveformRenderer).mockClear();
    });

    test("renders the samples returned by the endpoint", async () => {
        vi.stubGlobal(
            "fetch",
            vi.fn(() =>
                Promise.resolve({
                    ok: true,
                    status: 200,
                    json: () =>
                        Promise.resolve({
                            waveform: [1, 2, 3, 4],
                            waveform_sampling_rate: 2,
                            waveform_max: 4,
                        }),
                }),
            ),
        );

        const { renderer } = await mountWaveform();

        expect(renderer.render).toHaveBeenCalledWith(
            [
                { i: 0, v: 1 },
                { i: 1, v: 2 },
            ],
            4,
            expect.any(Number),
        );
    });

    // The endpoint answers a missing waveform with a JSON error body, so
    // parsing the response succeeds and only the status indicates the failure.
    test("renders an empty waveform when the endpoint returns 404", async () => {
        vi.stubGlobal(
            "fetch",
            vi.fn(() =>
                Promise.resolve({
                    ok: false,
                    status: 404,
                    json: () =>
                        Promise.resolve({ message: "Waveform not found." }),
                }),
            ),
        );

        const { renderer } = await mountWaveform();

        expect(renderer.render).toHaveBeenCalledWith([], 0, expect.any(Number));
    });

    test("renders an empty waveform when the request fails", async () => {
        vi.stubGlobal(
            "fetch",
            vi.fn(() => Promise.reject(new Error("network error"))),
        );

        const { renderer } = await mountWaveform();

        expect(renderer.render).toHaveBeenCalledWith([], 0, expect.any(Number));
    });
});

function headerSegment(): TranscriptSegment {
    return { ...segment(), start: 3.25, end: 7.5 };
}

describe("WaveformComponent header", () => {
    beforeEach(() => {
        setActivePinia(createPinia());
        vi.mocked(WaveformRenderer).mockClear();
        vi.stubGlobal(
            "fetch",
            vi.fn(() =>
                Promise.resolve({
                    ok: true,
                    status: 200,
                    json: () =>
                        Promise.resolve({
                            waveform: [1, 2, 3, 4],
                            waveform_sampling_rate: 2,
                            waveform_max: 4,
                        }),
                }),
            ),
        );
    });

    test("shows the start and end of the active segment, and nothing else", async () => {
        const { wrapper } = await mountWaveform(headerSegment());

        const header = wrapper.find(".waveform__header");
        const timecodes = header.findAllComponents(Timecode);
        expect(timecodes).toHaveLength(1);
        expect(timecodes[0].props()).toMatchObject({ start: 3.25, end: 7.5 });
        expect(header.text()).toBe("0:00:03.250–0:00:07.500");
    });
});

function wordSegment(): TranscriptSegment {
    return {
        ...segment(),
        start: 0,
        end: 2,
        words: [
            {
                id: "wrd_1",
                start: 0,
                end: 1,
                word: "hello",
                score: 1,
                speakerId: "spk_1",
            },
        ],
    };
}

describe("WaveformComponent word changes", () => {
    beforeEach(() => {
        setActivePinia(createPinia());
        vi.mocked(WaveformRenderer).mockClear();
        vi.stubGlobal(
            "fetch",
            vi.fn(() =>
                Promise.resolve({
                    ok: true,
                    status: 200,
                    json: () =>
                        Promise.resolve({
                            waveform: [1, 2, 3, 4],
                            waveform_sampling_rate: 2,
                            waveform_max: 4,
                        }),
                }),
            ),
        );
    });

    test("re-renders when a word of the active segment is renamed", async () => {
        const { renderer } = await mountWaveform(wordSegment());
        const before = renderer.render.mock.calls.length;

        useTranscriptStore().applyWordEdit(0, 0, "goodbye");
        await nextTick();

        expect(renderer.render.mock.calls.length).toBeGreaterThan(before);
    });

    test("re-renders when a word is inserted into the active segment", async () => {
        const { renderer } = await mountWaveform(wordSegment());
        const before = renderer.render.mock.calls.length;

        useTranscriptStore().insertRight(0, 0);
        await nextTick();

        expect(renderer.render.mock.calls.length).toBeGreaterThan(before);
    });

    test("re-renders when a word is deleted from the active segment", async () => {
        const { renderer } = await mountWaveform(wordSegment());
        const before = renderer.render.mock.calls.length;

        useTranscriptStore().deleteWord(0, 0);
        await nextTick();

        expect(renderer.render.mock.calls.length).toBeGreaterThan(before);
    });
});
