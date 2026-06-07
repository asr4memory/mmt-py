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

    test("render creates an SVG in the container", () => {
        const renderer = new WaveformRenderer(
            "#waveform-test",
            document.createElement("audio"),
            {
                getSegment: () => ({
                    id: 1,
                    start: 0,
                    end: 2,
                    text: "",
                    speaker: null,
                    words: [],
                }),
                onUpdateTimecode: () => {},
            },
        );

        renderer.render([], 100, 500);

        expect(container.querySelector("svg")).not.toBeNull();
    });
});
