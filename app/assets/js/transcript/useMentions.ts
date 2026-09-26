import type { Ref } from "vue";

import { newId } from "./new_id";
import type { Mention, TranscriptSegment } from "./types";

// The named-entity occurrence tier: resolving a word's mentionId and editing
// the mentions of a segment. The identity tier the mentions point at lives in
// the entities.
export function useMentions(
    segments: Ref<TranscriptSegment[]>,
    mentions: Ref<Record<string, Mention>>,
    pruneOrphans: () => void,
) {
    // Resolve a mentionId to its Mention, or null when the word is unlinked
    // or the mention is missing.
    function mention(mentionId?: string | null): Mention | null {
        if (!mentionId) return null;
        return mentions.value[mentionId] ?? null;
    }

    // Resolve a word's mentionId to its mention type, or null when the word
    // is unlinked or the mention is missing.
    function mentionType(mentionId?: string | null): string | null {
        return mention(mentionId)?.type ?? null;
    }

    // The full surface text of a mention: the words within the segment that
    // share the mentionId, joined in order. Mentions do not cross segments.
    function mentionText(
        segmentIndex: number,
        mentionId?: string | null,
    ): string {
        if (!mentionId) return "";
        const segment = segments.value[segmentIndex];
        if (!segment) return "";
        return segment.words
            .filter((word) => word.mentionId === mentionId)
            .map((word) => word.word)
            .join(" ");
    }

    // Turn a plain word into a named-entity mention: create a fresh mention
    // with a (guessed) type and point the word at it. The type can be
    // corrected afterwards via setMentionType.
    function createMention(
        segmentIndex: number,
        wordIndex: number,
        type: string,
    ) {
        const segment = segments.value[segmentIndex];
        const word = segment?.words[wordIndex];
        if (!word) return;
        const id = newId("men");
        mentions.value[id] = { type, score: 1, entityId: null };
        word.mentionId = id;
        segment.dirty = true;
    }

    // Grow a mention onto the word just past its span, left or right. Does
    // nothing at a segment edge or when the neighbour already belongs to a
    // mention (we never steal words between entities).
    function extendMention(
        segmentIndex: number,
        mentionId: string,
        direction: "left" | "right",
    ) {
        const segment = segments.value[segmentIndex];
        if (!segment) return;
        const indices = segment.words
            .map((word, i) => (word.mentionId === mentionId ? i : -1))
            .filter((i) => i >= 0);
        if (indices.length === 0) return;
        const target =
            direction === "left"
                ? indices[0] - 1
                : indices[indices.length - 1] + 1;
        const neighbour = segment.words[target];
        if (!neighbour || neighbour.mentionId) return;
        neighbour.mentionId = mentionId;
        segment.dirty = true;
    }

    // Shrink a mention by unlinking the word at one end of its span. Does
    // nothing for a single-word mention (removeMention covers that case).
    function reduceMention(
        segmentIndex: number,
        mentionId: string,
        direction: "left" | "right",
    ) {
        const segment = segments.value[segmentIndex];
        if (!segment) return;
        const indices = segment.words
            .map((word, i) => (word.mentionId === mentionId ? i : -1))
            .filter((i) => i >= 0);
        if (indices.length <= 1) return;
        const target =
            direction === "left" ? indices[0] : indices[indices.length - 1];
        segment.words[target].mentionId = null;
        segment.dirty = true;
    }

    // Remove a whole named-entity mention: unlink every word in the segment
    // that carries the mentionId and drop the mention itself. The words stay.
    function removeMention(segmentIndex: number, mentionId: string) {
        const segment = segments.value[segmentIndex];
        if (!segment) return;
        for (const word of segment.words) {
            if (word.mentionId === mentionId) {
                word.mentionId = null;
            }
        }
        delete mentions.value[mentionId];
        segment.dirty = true;
        pruneOrphans();
    }

    // Change the type of a mention. The words keep their link; only the
    // shared mention's classification changes.
    function setMentionType(
        segmentIndex: number,
        mentionId: string,
        type: string,
    ) {
        const target = mentions.value[mentionId];
        if (!target) return;
        target.type = type;
        const segment = segments.value[segmentIndex];
        if (segment) segment.dirty = true;
    }

    return {
        mention,
        mentionType,
        mentionText,
        createMention,
        extendMention,
        reduceMention,
        removeMention,
        setMentionType,
    };
}
