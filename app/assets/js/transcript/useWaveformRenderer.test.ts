import { beforeEach, describe, expect, test, vi } from "vitest";
import { defineComponent } from "vue";
import { mount } from "@vue/test-utils";

import { WaveformRenderer } from "./waveform_renderer";
import { useWaveformRenderer } from "./useWaveformRenderer";

vi.mock("./waveform_renderer", () => ({
    WaveformRenderer: vi.fn(function () {
        return { updateTime: vi.fn(), destroy: vi.fn() };
    }),
}));

describe("useWaveformRenderer", () => {
    beforeEach(() => {
        vi.mocked(WaveformRenderer).mockClear();
    });

    test("calls destroy on the renderer when the component unmounts", () => {
        const TestComponent = defineComponent({
            setup() {
                useWaveformRenderer(
                    "#waveform",
                    document.createElement("audio"),
                    () => undefined,
                    () => {},
                );
            },
            template: "<div></div>",
        });

        const wrapper = mount(TestComponent);
        const instance = vi.mocked(WaveformRenderer).mock.results[0].value;

        wrapper.unmount();

        expect(instance.destroy).toHaveBeenCalledOnce();
    });
});
