import { mapState, mapWritableState } from "pinia";

import { useTranscriptStore } from "../transcript_store";
import addIDsToTranscript from "../helpers/add_ids_to_transcript";
import beforeUnloadHandler from "../helpers/before_unload_handler";
import cleanTranscript from "../helpers/clean_transcript";
import updateTranscript from "../helpers/update_transcript";
import TranscriptSegment from "./transcript_segment";
import WaveformComponent from "./waveform_component";

const SEEK_TIME_LEFT = 5;
const SEEK_TIME_RIGHT = 5;

export default {
    components: {
        TranscriptSegment,
        WaveformComponent,
    },
    name: "TranscriptTable",
    props: ["id", "label", "mediaType", "uploadedFileId", "projectId"],
    data() {
        return {
            activeSegmentIdx: 0,
            currentTime: 0,
            transcriptLoaded: false,
            showConfidence: false,
            autoScroll: false,
            showWaveform: false,
        };
    },
    async mounted() {
        const path = `/transcripts/${this.id}/json/`;
        const result = await fetch(path);
        const json = await result.json();
        this.transcriptLoaded = true;
        this.segments = addIDsToTranscript(json.segments);
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
                segments: cleanedTranscript,
            });
            this.segments = cleanedTranscript;
        },
    },
    template: `
    <h1>{{ label }}</h1>

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
                <button type="button" @click="handleLeftSeek"> &longleftarrow;</button>
                <button type="button" @click="handleRightSeek">&longrightarrow;</button>
            </div>
            <p v-if="transcriptIsDirty" class="u-font-italic u-mt">
                {{$t('changed_segments', dirtySegmentCount, {count: dirtySegmentCount})}}
            </p>
            <p v-else class="u-font-italic u-mt">
                {{$t('no_changes')}}
            </p>
            <div class="u-mt">
                <button type="button" class="button button--primary" :disabled="!transcriptIsDirty"
                    @click="saveTranscript">{{$t('save_transcript')}}</button>
            </div>
            <div class="u-flex u-mt">
                <input type="checkbox" id="show-confidence" v-model="showConfidence" />
                <label for="show-confidence">{{$t('show_confidence')}}</label>
            </div>
            <div class="u-flex u-mt-small">
                <input type="checkbox" id="auto-scroll" v-model="autoScroll" />
                <label for="auto-scroll">{{$t('auto_scroll')}}</label>
            </div>
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
