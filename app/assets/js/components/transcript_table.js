import { mapState, mapWritableState } from "pinia";

import { useTranscriptStore } from "../transcript_store";
import updateTranscript from "../helpers/update_transcript";
import cleanTranscript from "../helpers/clean_transcript";
import TranscriptSegment from "./transcript_segment";

export default {
    components: {
        TranscriptSegment,
    },
    name: "TranscriptTable",
    props: ["id", "label", "mediaType", "uploadedFileId", "projectId"],
    data() {
        return {
            transcriptLoaded: false,
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
    },
    methods: {
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
            <video v-if="isVideo" id="media-player" controls width="240" class="transcript__media">
                <source :src="mediaFileURL"
                        :type="mediaType" />
            </video>
            <audio v-else id="media-player" controls width="240" class="transcript__media">
                <source :src="mediaFileURL"
                        :type="mediaType" />
            </audio>
            <div class="u-mt">
                <button type="button" class="button button--primary" :disabled="!transcriptIsDirty"
                    @click="saveTranscript">{{$t('save_transcript')}}</button>
            </div>
        </div>
        <div v-if="transcriptLoaded" spellcheck="false">
            <TranscriptSegment v-for="(segment, index) in segments"
                :key="segment.start"
                :segment="segment"
                :index="index" />
        </div>
        <p v-else>{{$t('loading_transcript')}}</p>
    </div>
    `,
};
