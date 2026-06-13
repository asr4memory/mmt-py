import { mapState, mapWritableState, mapActions } from "pinia";

import { useTranscriptStore } from "./transcript_store";
import addIDsToTranscript from "./add_ids_to_transcript";
import removeIDsFromTranscript from "./remove_ids_from_transcript";
import beforeUnloadHandler from "../shared/before_unload_handler";
import cleanTranscript from "./clean_transcript";
import findPlaybackPosition from "./find_playback_position";
import updateTranscript from "./update_transcript";
import TranscriptSegment from "./transcript_segment";
import TranscriptSubhead from "./transcript_subhead";
import TranscriptSidebar from "./transcript_sidebar";
import MediaBar from "./media_bar";

export default {
    components: {
        TranscriptSegment,
        TranscriptSubhead,
        TranscriptSidebar,
        MediaBar,
    },
    name: "TranscriptTable",
    props: [
        "id",
        "label",
        "mediaType",
        "language",
        "duration",
        "uploadedFile",
        "uploadedFileId",
        "projectId",
    ],
    data() {
        return {
            activeSegmentIdx: 0,
            currentSegmentIdx: -1,
            currentWordIdx: -1,
            transcriptLoaded: false,
            showConfidence: false,
            showEntities: true,
            showEdits: true,
            autoScroll: false,
            showWaveform: true,
        };
    },
    async mounted() {
        await this.loadTranscript();
    },
    beforeUnmount() {
        window.removeEventListener("beforeunload", beforeUnloadHandler);
    },
    computed: {
        ...mapState(useTranscriptStore, [
            "segments",
            "dirtySegmentCount",
            "transcriptIsDirty",
        ]),
        ...mapWritableState(useTranscriptStore, ["segments"]),
        mediaFileURL() {
            return `/uploaded-files/${this.uploadedFileId}/download/`;
        },
        activeSegment() {
            return this.segments[this.activeSegmentIdx];
        },
        activeWaveformSection() {
            if (!this.waveform) {
                return [];
            }

            const samplingRate = this.waveform.waveform_sampling_rate;

            const startIndex = Math.floor(
                this.activeSegment.start * samplingRate,
            );
            const endIndex = Math.floor(this.activeSegment.end * samplingRate);
            const result = this.waveform.waveform.slice(startIndex, endIndex);
            return result;
        },
    },
    watch: {
        transcriptIsDirty(newValue, oldValue) {
            if (newValue === true && oldValue === false) {
                window.addEventListener("beforeunload", beforeUnloadHandler);
            }
            if (newValue === false && oldValue === true) {
                window.removeEventListener("beforeunload", beforeUnloadHandler);
            }
        },
    },
    methods: {
        ...mapActions(useTranscriptStore, ["extractSpeakers"]),
        async loadTranscript() {
            const path = `/transcripts/${this.id}/json/`;
            const result = await fetch(path);
            const json = await result.json();
            this.segments = addIDsToTranscript(json.segments);
            this.extractSpeakers();
            this.transcriptLoaded = true;
        },
        async discardTranscript() {
            this.transcriptLoaded = false;
            await this.loadTranscript();
        },
        updateActiveSegment(newIndex) {
            this.activeSegmentIdx = newIndex;
            this.showWaveform = true;
        },
        handleCloseWaveformPanel() {
            this.showWaveform = false;
        },
        handleTimeUpdate(time) {
            const { segmentIdx, wordIdx } = findPlaybackPosition(
                this.segments,
                time,
            );
            this.currentSegmentIdx = segmentIdx;
            this.currentWordIdx = wordIdx;
        },
        async saveTranscript() {
            const cleanedTranscript = cleanTranscript(this.segments);
            const result = await updateTranscript(this.id, {
                segments: removeIDsFromTranscript(cleanedTranscript),
            });
            this.segments = cleanedTranscript;
        },
    },
    template: `
    <div class="container u-mt">
        <h1 class="u-mt-none u-mb-none"><b>{{ label }}</b></h1>
        <TranscriptSubhead :label="uploadedFile" :language="language" :duration="duration"
            @save="saveTranscript" @discard="discardTranscript" />
    </div>

    <MediaBar
        :transcriptId="id"
        :uploadedFileId="uploadedFileId"
        :activeSegmentIdx="activeSegmentIdx"
        :src="mediaFileURL"
        :mediaType="mediaType"
        :showWaveform="transcriptLoaded && showWaveform"
        @timeupdate="handleTimeUpdate"
        @close-panel="handleCloseWaveformPanel" />

    <div class="container u-mt u-mb-large">
        <div class="layout layout--transcript transcript">
            <div v-if="transcriptLoaded" spellcheck="false">
                <TranscriptSegment v-for="(segment, index) in segments"
                    @activate-segment="updateActiveSegment"
                    :key="segment.id"
                    :segment="segment"
                    :index="index"
                    :active="activeSegmentIdx === index"
                    :isCurrent="currentSegmentIdx === index"
                    :currentWordIdx="currentSegmentIdx === index ? currentWordIdx : -1"
                    :showConfidence="showConfidence"
                    :showEntities="showEntities"
                    :showEdits="showEdits"
                    :autoScroll="autoScroll" />
            </div>
            <p v-else>{{$t('loading_transcript')}}</p>
            <div class="transcript__media-column">
                <TranscriptSidebar
                    v-model:showConfidence="showConfidence"
                    v-model:showEntities="showEntities"
                    v-model:showEdits="showEdits"
                    v-model:autoScroll="autoScroll" />
            </div>

        </div>
    </div>
    `,
};
