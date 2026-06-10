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
    let playheadFrameId: number | null = null;

    function handleTimeUpdate() {
        renderer?.updateTime();
    }

    // Smooth playhead motion while playing; timeupdate alone only
    // fires a few times per second.
    function animatePlayhead() {
        renderer?.updatePlayhead();
        playheadFrameId = requestAnimationFrame(animatePlayhead);
    }

    function startPlayheadLoop() {
        if (playheadFrameId !== null) return;
        playheadFrameId = requestAnimationFrame(animatePlayhead);
    }

    function stopPlayheadLoop() {
        if (playheadFrameId === null) return;
        cancelAnimationFrame(playheadFrameId);
        playheadFrameId = null;
    }

    onMounted(() => {
        renderer = new WaveformRenderer(containerSelector, mediaElement, {
            getSegment,
            onUpdateTimecode,
        });
        mediaElement.addEventListener("timeupdate", handleTimeUpdate);
        mediaElement.addEventListener("play", startPlayheadLoop);
        mediaElement.addEventListener("pause", stopPlayheadLoop);
        mediaElement.addEventListener("ended", stopPlayheadLoop);
        if (!mediaElement.paused) startPlayheadLoop();
    });

    onBeforeUnmount(() => {
        mediaElement.removeEventListener("timeupdate", handleTimeUpdate);
        mediaElement.removeEventListener("play", startPlayheadLoop);
        mediaElement.removeEventListener("pause", stopPlayheadLoop);
        mediaElement.removeEventListener("ended", stopPlayheadLoop);
        stopPlayheadLoop();
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
