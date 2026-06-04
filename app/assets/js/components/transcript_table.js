import { mapState, mapWritableState, mapActions } from "pinia";

import { useTranscriptStore } from "../transcript_store";
import addIDsToTranscript from "../helpers/add_ids_to_transcript";
import removeIDsFromTranscript from "../helpers/remove_ids_from_transcript";
import beforeUnloadHandler from "../helpers/before_unload_handler";
import cleanTranscript from "../helpers/clean_transcript";
import updateTranscript from "../helpers/update_transcript";
import TranscriptSegment from "./transcript_segment";
import TranscriptSubhead from "./transcript_subhead";
import TranscriptSidebar from "./transcript_sidebar";
import WaveformComponent from "./waveform_component";

const SEEK_TIME_LEFT = 5;
const SEEK_TIME_RIGHT = 5;

export default {
    components: {
        TranscriptSegment,
        TranscriptSubhead,
        TranscriptSidebar,
        WaveformComponent,
    },
    name: "TranscriptTable",
    props: ["id", "label", "mediaType", "language", "duration", "uploadedFile", "uploadedFileId", "projectId"],
    data() {
        return {
            activeSegmentIdx: 0,
            currentTime: 0,
            transcriptLoaded: false,
            showConfidence: false,
            showEntities: true,
            showEdits: true,
            autoScroll: false,
            showWaveform: false,
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
        isVideo() {
            return this.mediaType.startsWith("video");
        },
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
        handleTimeUpdate(event) {
            this.currentTime = this.$refs.media.currentTime;
        },
        handleLeftSeek(event) {
            const mediaPlayer = this.$refs.media;
            mediaPlayer.currentTime = mediaPlayer.currentTime - SEEK_TIME_LEFT;
            mediaPlayer.play();
        },
        handleRightSeek(event) {
            const mediaPlayer = this.$refs.media;
            mediaPlayer.currentTime = mediaPlayer.currentTime + SEEK_TIME_RIGHT;
            mediaPlayer.play();
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
    <h1 class="u-mb-none"><b>{{ label }}</b></h1>
    <TranscriptSubhead :label="uploadedFile" :language="language" :duration="duration" @save="saveTranscript" @discard="discardTranscript" class="u-mb" />

    <div class="layout layout--transcript transcript">
        <div class="transcript__media-column">
            <video v-if="isVideo" id="media-player" ref="media" controls
                width="240" class="transcript__media" @timeupdate="handleTimeUpdate">
                <source :src="mediaFileURL" :type="mediaType" />
            </video>
            <audio v-else id="media-player" ref="media" controls
                width="240" class="transcript__media" @timeupdate="handleTimeUpdate">
                <source :src="mediaFileURL" :type="mediaType" />
            </audio>
            <div>
                <button type="button" @click="handleLeftSeek">&#9194;</button>
                <button type="button" @click="handleRightSeek">&#9193;</button>
            </div>

            <TranscriptSidebar
                v-model:showConfidence="showConfidence"
                v-model:showEntities="showEntities"
                v-model:showEdits="showEdits"
                v-model:autoScroll="autoScroll" />
        </div>
        <div v-if="transcriptLoaded" spellcheck="false">
            <TranscriptSegment v-for="(segment, index) in segments"
                @activate-segment="updateActiveSegment"
                :key="segment.id"
                :segment="segment"
                :index="index"
                :active="activeSegmentIdx === index"
                :currentTime="currentTime"
                :showConfidence="showConfidence"
                :showEntities="showEntities"
                :showEdits="showEdits"
                :autoScroll="autoScroll" />
        </div>
        <p v-else>{{$t('loading_transcript')}}</p>
        <WaveformComponent v-if="transcriptLoaded && showWaveform"
            :transcriptId="id"
            :uploadedFileId="uploadedFileId"
            :activeSegmentIdx="activeSegmentIdx"
            :mediaElement="$refs.media"
            @close-panel="handleCloseWaveformPanel" />
    </div>
    `,
};
