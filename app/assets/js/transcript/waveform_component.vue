<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import formatTimecode from "../shared/format_timecode";
import { routes } from "../shared/routes";
import { useTranscriptStore } from "./transcript_store";
import type { TranscriptSegment, WaveformSample } from "./useWaveformRenderer";
import { useWaveformRenderer } from "./useWaveformRenderer";
import { HORIZONTAL_PIXELS_PER_SECOND } from "./waveform_renderer";

const SEEK_TIME_WAVEFORM = 0.5;

const props = defineProps<{
    transcriptId: number;
    uploadedFileId: number;
    activeSegmentIdx: number;
    mediaElement: HTMLMediaElement;
}>();

const store = useTranscriptStore();
const { updateTimecode } = store;

const waveform = ref<number[]>([]);
const samplingRate = ref(0);
const maximumAmplitude = ref(0);

const activeSegment = computed<TranscriptSegment | undefined>(
    () => (store.segments as TranscriptSegment[])[props.activeSegmentIdx],
);

const duration = computed(() => {
    const seg = activeSegment.value;
    return seg ? seg.end - seg.start : 0;
});

const formattedID = computed(() => activeSegment.value?.id.slice(0, 8) ?? "");

const startTimecode = computed(() =>
    activeSegment.value ? formatTimecode(activeSegment.value.start) : undefined,
);

const endTimecode = computed(() =>
    activeSegment.value ? formatTimecode(activeSegment.value.end) : undefined,
);

const formattedDuration = computed(() =>
    activeSegment.value
        ? (activeSegment.value.end - activeSegment.value.start).toFixed(2)
        : undefined,
);

const waveformWithIDs = computed<WaveformSample[]>(() =>
    waveform.value.map((v, i) => ({ i, v })),
);

const visibleSamples = computed<WaveformSample[]>(() => {
    const seg = activeSegment.value;
    if (!seg) return [];
    return waveformWithIDs.value.slice(
        Math.floor(seg.start * samplingRate.value),
        Math.floor(seg.end * samplingRate.value),
    );
});

const waveformWidth = computed(
    () => duration.value * HORIZONTAL_PIXELS_PER_SECOND,
);

const { render } = useWaveformRenderer(
    "#waveform",
    props.mediaElement,
    () => activeSegment.value,
    updateTimecode,
);

function renderSegment() {
    render(visibleSamples.value, maximumAmplitude.value, waveformWidth.value);
}

onMounted(async () => {
    try {
        const response = await fetch(
            routes.uploadedFileWaveform(props.uploadedFileId),
        );
        // The endpoint answers a missing waveform with a JSON error body,
        // so parsing the response succeeds and only the status indicates
        // the failure.
        if (!response.ok) {
            throw new Error(
                `Waveform request failed with status ${response.status}.`,
            );
        }
        const data = await response.json();
        waveform.value = data.waveform;
        samplingRate.value = data.waveform_sampling_rate;
        maximumAmplitude.value = data.waveform_max;
    } catch {
        waveform.value = [];
        samplingRate.value = 0;
        maximumAmplitude.value = 0;
    }
    renderSegment();
});

watch(() => props.activeSegmentIdx, renderSegment);

function togglePlayback() {
    if (props.mediaElement.paused) {
        props.mediaElement.play();
    } else {
        props.mediaElement.pause();
    }
}

function seekBackward(event: Event) {
    event.preventDefault();
    props.mediaElement.currentTime -= SEEK_TIME_WAVEFORM;
}

function seekForward(event: Event) {
    event.preventDefault();
    props.mediaElement.currentTime += SEEK_TIME_WAVEFORM;
}
</script>

<template>
    <div class="waveform">
        <header class="waveform__header">
            <span class="waveform__header-id">#{{ formattedID }}</span>
            <span class="waveform__header-timecode"
                >{{ startTimecode }}–{{ endTimecode }}</span
            >
            <span class="waveform__header-duration">({{ formattedDuration }}s)</span>
        </header>
        <!-- Set tabindex so that div can be focused and receive key events. -->
        <div
            id="waveform"
            class="waveform__container"
            tabindex="0"
            @keydown.space.prevent
            @keyup.space="togglePlayback"
            @keyup.left="seekBackward"
            @keyup.right="seekForward"
        ></div>
    </div>
</template>
