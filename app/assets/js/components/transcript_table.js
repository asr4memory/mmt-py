import { mapState, mapWritableState } from "pinia";

import { useTranscriptStore } from "../transcript_store";
import updateTranscript from '../helpers/update_transcript';
import TranscriptSegment from "./transcript_segment";

function cleanTranscript(segments) {
    if (!Array.isArray(segments)) {
        throw TypeError('segments must be an array');
    }

    const result = segments.map((segment) => {
        const cleanedWordsArray = segment.words.map((word) => {
            const clonedWord = {...word};
            delete clonedWord.dirty;
            return clonedWord;
        });

        return {
            ...segment,
            words: cleanedWordsArray,
        };
    });

    return result;
}

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
