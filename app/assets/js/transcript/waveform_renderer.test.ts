import { afterEach, beforeEach, describe, expect, test } from "vitest";

import { WaveformRenderer } from "./waveform_renderer";

describe("WaveformRenderer", () => {
    let container: HTMLDivElement;

    beforeEach(() => {
        container = document.createElement("div");
        container.id = "waveform-test";
        document.body.appendChild(container);
    });

    afterEach(() => {
        document.body.removeChild(container);
    });

    const renderWithWidth = (
        start: number,
        end: number,
        width: number,
    ) => {
        const renderer = new WaveformRenderer(
            "#waveform-test",
            document.createElement("audio"),
            {
                getSegment: () => ({
                    id: 1,
                    start,
                    end,
                    text: "",
                    speakerId: null,
                    words: [],
                }),
                onUpdateTimecode: () => {},
            },
        );
        renderer.render([], 100, width);
        return renderer;
    };

    const tickCount = () =>
        container.querySelectorAll(".waveform__axis-group .tick").length;

    test("render creates an SVG in the container", () => {
        renderWithWidth(0, 2, 500);

        expect(container.querySelector("svg")).not.toBeNull();
    });

    test("axis tick density scales with the waveform width", () => {
        // A short (narrow) segment must not cram in too many ticks, and a long
        // (wide) one must not be left sparse: density stays roughly constant.
        renderWithWidth(0, 2, 500);
        const narrowTicks = tickCount();

        renderWithWidth(0, 60, 15000);
        const wideTicks = tickCount();

        expect(narrowTicks).toBeGreaterThanOrEqual(2);
        expect(narrowTicks).toBeLessThanOrEqual(6);
        expect(wideTicks).toBeGreaterThan(narrowTicks * 5);
    });
});
