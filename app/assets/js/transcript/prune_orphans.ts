import type { Ref } from "vue";

import type { Entity, Mention, Redaction, TranscriptSegment } from "./types";

// Drop mentions, redactions and entities that nothing references any more.
// The stored format rejects an entry that no word (or, for an entity, no
// mention) points at, so every operation that removes words or mentions runs
// this afterwards. The pass cascades: a mention whose last word is gone is
// removed first, and an entity that loses its last mention with it.
export function pruneOrphans(
    segments: Ref<TranscriptSegment[]>,
    mentions: Ref<Record<string, Mention>>,
    redactions: Ref<Record<string, Redaction>>,
    entities: Ref<Record<string, Entity>>,
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

    const referencedEntityIds = new Set<string>();
    for (const mention of Object.values(mentions.value)) {
        if (mention.entityId) referencedEntityIds.add(mention.entityId);
    }
    for (const entityId of Object.keys(entities.value)) {
        if (!referencedEntityIds.has(entityId)) {
            delete entities.value[entityId];
        }
    }
}
