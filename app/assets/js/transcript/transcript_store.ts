import { defineStore } from "pinia";
import { ref } from "vue";

import { pruneOrphans as pruneOrphansIn } from "./prune_orphans";
import type {
    Entity,
    Mention,
    Redaction,
    Speaker,
    TranscriptSegment,
} from "./types";
import { useMentions } from "./useMentions";
import { useRedactions } from "./useRedactions";
import { useSegments } from "./useSegments";
import { useSpeakers } from "./useSpeakers";
import { useWords } from "./useWords";

// The state of the transcript editor. The operations live in one composable
// per tier; this store holds the state they share and exposes their functions
// under one name.
export const useTranscriptStore = defineStore("transcript", () => {
    const segments = ref<TranscriptSegment[]>([]);
    const speakers = ref<Speaker[]>([]);
    const mentions = ref<Record<string, Mention>>({});
    // The identity tier: one entry per canonical entity, referenced by a
    // mention's entityId.
    const entities = ref<Record<string, Entity>>({});
    // The second occurrence tier, independent of the mentions: one entry per
    // redacted run of words, referenced by a word's redactionId.
    const redactions = ref<Record<string, Redaction>>({});

    function pruneOrphans() {
        pruneOrphansIn(segments, mentions, redactions, entities);
    }

    const words = useWords(segments, pruneOrphans);
    const mentionOperations = useMentions(segments, mentions, pruneOrphans);
    const redactionOperations = useRedactions(segments, redactions);
    const speakerOperations = useSpeakers(segments, speakers);
    const segmentOperations = useSegments(segments, speakers, pruneOrphans);

    return {
        segments,
        speakers,
        mentions,
        entities,
        redactions,
        ...words,
        ...mentionOperations,
        ...redactionOperations,
        ...speakerOperations,
        ...segmentOperations,
    };
});
