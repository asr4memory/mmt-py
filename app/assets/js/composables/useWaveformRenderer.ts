import { onBeforeUnmount, onMounted } from "vue";

import { WaveformRenderer } from "../components/waveform_renderer";
import type {
    TranscriptSegment,
    WaveformRendererOptions,
    WaveformSample,
} from "../components/waveform_renderer";

export type { TranscriptSegment, WaveformSample };
export type { TranscriptWord } from "../components/waveform_renderer";

export function useWaveformRenderer(
    containerSelector: string,
    mediaElement: HTMLMediaElement,
    getSegment: () => TranscriptSegment | undefined,
    onUpdateTimecode: WaveformRendererOptions["onUpdateTimecode"],
) {
    let renderer: WaveformRenderer | null = null;

    function handleTimeUpdate() {
        renderer?.updateTime();
    }

    onMounted(() => {
        renderer = new WaveformRenderer(containerSelector, mediaElement, {
            getSegment,
            onUpdateTimecode,
        });
        mediaElement.addEventListener("timeupdate", handleTimeUpdate);
    });

    onBeforeUnmount(() => {
        mediaElement.removeEventListener("timeupdate", handleTimeUpdate);
        renderer?.destroy();
        renderer = null;
    });

    function render(
        visibleSamples: WaveformSample[],
        maximumAmplitude: number,
        waveformWidth: number,
    ) {
        renderer?.render(visibleSamples, maximumAmplitude, waveformWidth);
    }

    return { render };
}
