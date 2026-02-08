import { mapState, mapWritableState } from "pinia";

import { useTranscriptStore } from "../transcript_store";
import updateTranscript from '../helpers/update_transcript';
import cleanTranscript from '../helpers/clean_transcript';
import TranscriptSegment from "./transcript_segment";

export default {
    components: {
        TranscriptSegment,
    },
    name: "TranscriptTable",
    props: ["id", "uploadedFileId", "projectId"],
    data() {
        return {
            transcriptLoaded: false,
        };
    },
    computed: {
        ...mapState(useTranscriptStore, ["segments", "transcriptIsDirty"]),
        ...mapWritableState(useTranscriptStore, ["segments"]),
    },
    methods: {
        async saveTranscript() {
            const cleanedTranscript = cleanTranscript(this.segments);
            const result = await updateTranscript(this.id, { segments: cleanedTranscript });
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
    <div v-if="transcriptLoaded">
        <TranscriptSegment v-for="(segment, index) in segments"
            :key="segment.start"
            :segment="segment"
            :index="index" />
        <div class="u-mt">
            <button type="button" :disabled="!transcriptIsDirty"
                @click="saveTranscript">Save transcript</button>
        </div>
    </div>
    <p v-else>{{ $t('loading_transcript') }}</p>
    `,
};
