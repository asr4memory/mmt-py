import TranscriptSegment from "./transcript_segment";
import { mapState, mapWritableState } from "pinia";

import { useTranscriptStore } from "../transcript_store";
import updateTranscript from '../helpers/update_transcript';

export default {
    components: {
        TranscriptSegment,
    },
    name: "TranscriptTable",
    props: ["id", "projectId"],
    data() {
        return {
            transcriptLoaded: false,
        };
    },
    computed: {
        ...mapState(useTranscriptStore, ["segments"]),
        ...mapWritableState(useTranscriptStore, ["segments"]),
    },
    methods: {
        async saveTranscript() {
            console.log('hello');
            const result = await updateTranscript(this.id, { segments: this.segments });
            console.log(result);
        },
    },
    async mounted() {
        const path = `/transcripts/${this.id}/json/`;
        const result = await fetch(path);
        const json = await result.json();
        this.transcriptLoaded = true;
        this.segments = json.segments;
        console.log(json);
    },
    template: `
    <section>
        <div v-if="transcriptLoaded" class="u-mt">
            <TranscriptSegment v-for="(segment, index) in segments"
                :key="segment.start" :start="segment.start" :end="segment.end"
                :index="index"
                :text="segment.text" :speaker="segment.speaker"
                :words="segment.words" />
            <div class="u-mt">
                <button type="button" @click="saveTranscript">Save transcript</button>
            </div>
        </div>
        <p v-else>{{ $t('loading_transcript') }}</p>
    </section>
    `,
};
