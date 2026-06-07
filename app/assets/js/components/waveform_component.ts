import {
    computed,
    defineComponent,
    onMounted,
    PropType,
    ref,
    watch,
} from "vue";

import { useTranscriptStore } from "../transcript_store";
import formatTimecode from "../helpers/format_timecode";
import { HORIZONTAL_PIXELS_PER_SECOND } from "./waveform_renderer";
import { useWaveformRenderer } from "../composables/useWaveformRenderer";
import type {
    TranscriptSegment,
    WaveformSample,
} from "../composables/useWaveformRenderer";

const SEEK_TIME_WAVEFORM = 0.5;

export default defineComponent({
    name: "WaveformComponent",
    props: {
        transcriptId: { type: Number, required: true },
        uploadedFileId: { type: Number, required: true },
        activeSegmentIdx: { type: Number, required: true },
        mediaElement: {
            type: Object as PropType<HTMLMediaElement>,
            required: true,
        },
    },
    setup(props) {
        const store = useTranscriptStore();
        const { updateTimecode } = store;

        const waveform = ref<number[]>([]);
        const samplingRate = ref(0);
        const maximumAmplitude = ref(0);

        const activeSegment = computed<TranscriptSegment | undefined>(
            () =>
                (store.segments as TranscriptSegment[])[props.activeSegmentIdx],
        );

        const duration = computed(() => {
            const seg = activeSegment.value;
            return seg ? seg.end - seg.start : 0;
        });

        const formattedID = computed(() =>
            String(activeSegment.value?.id ?? "").padStart(3, "0"),
        );

        const startTimecode = computed(() =>
            activeSegment.value
                ? formatTimecode(activeSegment.value.start)
                : undefined,
        );

        const endTimecode = computed(() =>
            activeSegment.value
                ? formatTimecode(activeSegment.value.end)
                : undefined,
        );

        const formattedDuration = computed(() =>
            activeSegment.value
                ? (activeSegment.value.end - activeSegment.value.start).toFixed(
                      2,
                  )
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
            render(
                visibleSamples.value,
                maximumAmplitude.value,
                waveformWidth.value,
            );
        }

        onMounted(async () => {
            try {
                const response = await fetch(
                    `/uploaded-files/${props.uploadedFileId}/waveform/`,
                );
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

        return {
            formattedID,
            startTimecode,
            endTimecode,
            formattedDuration,
            togglePlayback,
            seekBackward,
            seekForward,
        };
    },
    template: `
    <div class="waveform">
        <header class="waveform__header">
            <span>#{{formattedID}} {{startTimecode}}–{{endTimecode}} ({{formattedDuration}}s)</span>
        </header>
        <!-- Set tabindex so that div can be focused and receive key events. -->
        <div id="waveform"
            class="waveform__container"
            tabindex="0"
            @keydown.space.prevent
            @keyup.space="togglePlayback"
            @keyup.left="seekBackward"
            @keyup.right="seekForward"></div>
    </div>
    `,
});
