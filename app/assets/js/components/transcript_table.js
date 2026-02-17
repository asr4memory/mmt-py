import { mapState, mapWritableState } from "pinia";

import { useTranscriptStore } from "../transcript_store";
import updateTranscript from "../helpers/update_transcript";
import cleanTranscript from "../helpers/clean_transcript";
import TranscriptSegment from "./transcript_segment";
import WaveformComponent from "./waveform_component";

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
            transcriptLoaded: false,
            showConfidence: false,
        };
    },
    computed: {
        ...mapState(useTranscriptStore, ["segments", "transcriptIsDirty"]),
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
    methods: {
        updateActiveSegment(newIndex) {
            this.activeSegmentIdx = newIndex;
        },
        async saveTranscript() {
            const cleanedTranscript = cleanTranscript(this.segments);
            const result = await updateTranscript(this.id, {
                segments: cleanedTranscript,
            });
            this.segments = cleanedTranscript;
        },
    },
    async mounted() {
        const path = `/transcripts/${this.id}/json/`;
        const result = await fetch(path);
        const json = await result.json();
        this.transcriptLoaded = true;
        this.segments = json.segments;
    },
    template: `
    <h1>{{ label }}</h1>

    <div class="layout layout--transcript transcript">
        <div class="transcript__media-column">
            <video v-if="isVideo" id="media-player" ref="media" controls width="240" class="transcript__media">
                <source :src="mediaFileURL"
                        :type="mediaType" />
            </video>
            <audio v-else id="media-player" ref="media" controls width="240" class="transcript__media">
                <source :src="mediaFileURL"
                        :type="mediaType" />
            </audio>
            <div class="u-mt">
                <button type="button" class="button button--primary" :disabled="!transcriptIsDirty"
                    @click="saveTranscript">{{$t('save_transcript')}}</button>
            </div>
            <div class="u-flex u-mt">
                <input type="checkbox" id="checkbox" v-model="showConfidence" />
                <label for="checkbox">{{$t('show_confidence')}}</label>
            </div>
        </div>
        <div v-if="transcriptLoaded" spellcheck="false">
            <TranscriptSegment v-for="(segment, index) in segments"
                @activate-segment="updateActiveSegment"
                :key="segment.start"
                :segment="segment"
                :index="index"
                :active="activeSegmentIdx === index"
                :showConfidence="showConfidence" />
        </div>
        <p v-else>{{$t('loading_transcript')}}</p>
        <WaveformComponent v-if="transcriptLoaded"
            :transcriptId="id"
            :uploadedFileId="uploadedFileId"
            :activeSegmentIdx="activeSegmentIdx"
            :mediaElement="$refs.media" />
    </div>
    `,
};
