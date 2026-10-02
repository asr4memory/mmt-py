import type { Ref } from "vue";

import type { Mention, Redaction, TranscriptSegment } from "./types";

// Drop mentions and redactions that no word references any more. The stored
// format rejects such an entry, so every operation that removes words or
// mentions runs this afterwards. Entities are kept: an entity without
// mentions is legal.
export function pruneOrphans(
    segments: Ref<TranscriptSegment[]>,
    mentions: Ref<Record<string, Mention>>,
    redactions: Ref<Record<string, Redaction>>,
) {
    const referencedMentionIds = new Set<string>();
    const referencedRedactionIds = new Set<string>();
    for (const segment of segments.value) {
        for (const word of segment.words) {
            if (word.mentionId) referencedMentionIds.add(word.mentionId);
            if (word.redactionId) referencedRedactionIds.add(word.redactionId);
        }
    }
    for (const mentionId of Object.keys(mentions.value)) {
        if (!referencedMentionIds.has(mentionId)) {
            delete mentions.value[mentionId];
        }
    }
    for (const redactionId of Object.keys(redactions.value)) {
        if (!referencedRedactionIds.has(redactionId)) {
            delete redactions.value[redactionId];
        }
    }
}
