import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, test, vi } from "vitest";

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

async function mountWaveform() {
    const store = useTranscriptStore();
    store.segments = [segment()];

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
