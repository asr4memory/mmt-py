import { mapState, mapActions } from "pinia";

import { useTranscriptStore } from "../transcript_store";
import formatTimecode from "../helpers/format_timecode";
import { WaveformRenderer, HORIZONTAL_PIXELS_PER_SECOND } from "./waveform_renderer";

const SEEK_TIME_WAVEFORM = 0.5;

export default {
    components: {},
    name: "WaveformComponent",
    props: {
        transcriptId: Number,
        uploadedFileId: Number,
        activeSegmentIdx: Number,
        mediaElement: HTMLMediaElement,
    },
    emits: ["close-panel"],
    data() {
        return {
            waveform: [],
            samplingRate: 0,
            maximumAmplitude: 0,
        };
    },
    async mounted() {
        await this.prepareWaveForm();
        this.renderer = new WaveformRenderer("#waveform", this.mediaElement, {
            getSegment: () => this.activeSegment,
            onUpdateTimecode: this.updateTimecode,
        });
        this.timeUpdateHandler = () => this.renderer.updateTime();
        this.mediaElement.addEventListener("timeupdate", this.timeUpdateHandler);
        this.renderSegment();
    },
    beforeUnmount() {
        this.mediaElement.removeEventListener("timeupdate", this.timeUpdateHandler);
        this.renderer.destroy();
    },
    watch: {
        activeSegmentIdx() {
            this.renderSegment();
        },
    },
    computed: {
        ...mapState(useTranscriptStore, ["segments"]),
        formattedID() {
            return String(this.activeSegment.id).padStart(3, "0");
        },
        activeSegment() {
            if (this.segments) {
                return this.segments[this.activeSegmentIdx];
            }
        },
        duration() {
            return this.activeSegment.end - this.activeSegment.start;
        },
        startTimecode() {
            if (this.activeSegment) {
                return formatTimecode(this.activeSegment.start);
            }
        },
        endTimecode() {
            if (this.activeSegment) {
                return formatTimecode(this.activeSegment.end);
            }
        },
        formattedDuration() {
            if (this.activeSegment) {
                return (
                    this.activeSegment.end - this.activeSegment.start
                ).toFixed(2);
            }
        },
        waveformWithIDs() {
            return this.waveform.map((value, index) => ({
                i: index,
                v: value,
            }));
        },
        visibleSamples() {
            return this.waveformWithIDs.slice(
                Math.floor(this.activeSegment.start * this.samplingRate),
                Math.floor(this.activeSegment.end * this.samplingRate),
            );
        },
        waveformWidth() {
            return this.duration * HORIZONTAL_PIXELS_PER_SECOND;
        },
    },
    methods: {
        ...mapActions(useTranscriptStore, ["updateTimecode"]),
        async prepareWaveForm() {
            try {
                const response = await fetch(
                    `/uploaded-files/${this.uploadedFileId}/waveform/`,
                );
                const waveformData = await response.json();
                this.waveform = waveformData.waveform;
                this.samplingRate = waveformData.waveform_sampling_rate;
                this.maximumAmplitude = waveformData.waveform_max;
            } catch {
                this.waveform = null;
                this.samplingRate = null;
                this.maximumAmplitude = null;
            }
        },
        renderSegment() {
            this.renderer.render(
                this.visibleSamples,
                this.maximumAmplitude,
                this.waveformWidth,
            );
        },

        // Keyboard handlers
        togglePlayback() {
            if (this.mediaElement.paused) {
                this.mediaElement.play();
            } else {
                this.mediaElement.pause();
            }
        },
        seekBackward(event) {
            event.preventDefault();
            this.mediaElement.currentTime -= SEEK_TIME_WAVEFORM;
        },
        seekForward(event) {
            event.preventDefault();
            this.mediaElement.currentTime += SEEK_TIME_WAVEFORM;
        },
    },
    template: `
    <div class="waveform">
        <header class="waveform__header">
            <span>#{{formattedID}} {{startTimecode}}–{{endTimecode}} ({{formattedDuration}}s)</span>
            <button type="button" class="waveform__close"
                @click="$emit('closePanel')">&times;</button>
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
};
