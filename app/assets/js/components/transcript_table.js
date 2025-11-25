import TranscriptSegment from "./transcript_segment";
import { mapState, mapWritableState, mapActions } from "pinia";

import { useTranscriptStore } from "../transcript_store";

export default {
    components: {
        TranscriptSegment,
    },
    name: "TranscriptTable",
    props: ["id", "projectId"],
    data() {
        return {
            //segments: [],
            transcriptLoaded: false,
        };
    },
    computed: {
        ...mapState(useTranscriptStore, ["segments"]),
        ...mapWritableState(useTranscriptStore, ["segments"]),
    },
    async mounted() {
        const path = `/projects/${this.projectId}/transcripts/${this.id}/json/`;
        const result = await fetch(path);
        const json = await result.json();
        this.transcriptLoaded = true;
        this.segments = json.segments;
        console.log(json);
    },
    template: `
    <section>
        <h2>Transcript no. {{id}}</h2>
        <div v-if="transcriptLoaded" class="u-mt">
            <TranscriptSegment v-for="(segment, index) in segments"
                :key="segment.start" :start="segment.start" :end="segment.end"
                :index="index"
                :text="segment.text" :speaker="segment.speaker"
                :words="segment.words" />
        </div>
        <p v-else>{{ $t('loading_transcript') }}</p>
    </section>
    `,
};
