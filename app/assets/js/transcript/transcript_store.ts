import { defineStore } from "pinia";
import { computed, ref } from "vue";

import type {
    Entity,
    Mention,
    Redaction,
    Speaker,
    TranscriptSegment,
    TranscriptWord,
} from "./types";

const SPEAKER_COLORS = ["#5b9bd5", "#70ad47", "#ed7d31", "#9b59b6", "#17a589"];

function newId(prefix: string): string {
    return `${prefix}_${crypto.randomUUID()}`;
}

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

    // Resolve a mentionId to its Mention, or null when the word is unlinked
    // or the mention is missing.
    function mention(mentionId?: string | null): Mention | null {
        if (!mentionId) return null;
        return mentions.value[mentionId] ?? null;
    }

    // Resolve a word's mentionId to its NER label, or null when the word
    // is unlinked or the mention is missing.
    function mentionLabel(mentionId?: string | null): string | null {
        return mention(mentionId)?.label ?? null;
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

    // Resolve a redactionId to its Redaction, or null when the word is
    // unlinked or the redaction is missing.
    function redaction(redactionId?: string | null): Redaction | null {
        if (!redactionId) return null;
        return redactions.value[redactionId] ?? null;
    }

    // The full surface text of a redaction: the words within the segment that
    // share the redactionId, joined in order. Redactions do not cross
    // segments.
    function redactionText(
        segmentIndex: number,
        redactionId?: string | null,
    ): string {
        if (!redactionId) return "";
        const segment = segments.value[segmentIndex];
        if (!segment) return "";
        return segment.words
            .filter((word) => word.redactionId === redactionId)
            .map((word) => word.word)
            .join(" ");
    }

    const dirtySegmentCount = computed(() => {
        const dirtySegments = segments.value.filter(
            (segment) =>
                segment.dirty === true ||
                segment.words.some((word) => word.dirty === true),
        );
        return dirtySegments.length;
    });

    const transcriptIsDirty = computed(() => dirtySegmentCount.value > 0);

    function updateWord(segmentIndex: number, wordIndex: number, text: string) {
        const trimmedText = text.trim();
        const segment = segments.value[segmentIndex];
        const word = {
            ...segment.words[wordIndex],
        };
        const oldWord = word.word;

        if (trimmedText !== oldWord) {
            word.dirty = true;
        }

        if (trimmedText === "") {
            // Delete word.
            segment.words = segment.words
                .slice(0, wordIndex)
                .concat(segment.words.slice(wordIndex + 1));
            segment.dirty = true;
        } else if (trimmedText.split(" ").length === 1) {
            // Single word has changed.
            word.word = trimmedText;
            segment.words = segment.words
                .slice(0, wordIndex)
                .concat(word)
                .concat(segment.words.slice(wordIndex + 1));
        } else {
            // Former word contains more than one word now; split them up. Each
            // split word needs its own id so ids stay unique in the content.
            const splitWords = trimmedText.split(" ");
            const wordObjects = splitWords.map((w, i) => ({
                ...word,
                id: i === 0 ? word.id : newId("wrd"),
                word: w,
            }));
            const combined = segment.words
                .slice(0, wordIndex)
                .concat(wordObjects)
                .concat(segment.words.slice(wordIndex + 1));

            segment.words = combined;
        }
    }

    function insertLeft(segmentIndex: number, wordIndex: number) {
        const segment = segments.value[segmentIndex];
        const relativeWord = segment.words[wordIndex];
        const newWord: TranscriptWord = {
            id: newId("wrd"),
            start: relativeWord.start - 0.5,
            end: relativeWord.start - 0.05,
            word: "newword",
            score: 1,
            speakerId: relativeWord.speakerId,
            dirty: true,
        };
        segment.words = segment.words
            .slice(0, wordIndex)
            .concat(newWord)
            .concat(segment.words.slice(wordIndex));
    }

    function insertRight(segmentIndex: number, wordIndex: number) {
        const segment = segments.value[segmentIndex];
        const relativeWord = segment.words[wordIndex];
        const newWord: TranscriptWord = {
            id: newId("wrd"),
            start: relativeWord.end + 0.05,
            end: relativeWord.end + 0.5,
            word: "newword",
            score: 1,
            speakerId: relativeWord.speakerId,
            dirty: true,
        };
        segment.words = segment.words
            .slice(0, wordIndex + 1)
            .concat(newWord)
            .concat(segment.words.slice(wordIndex + 1));
    }

    function deleteWord(segmentIndex: number, wordIndex: number) {
        const segment = segments.value[segmentIndex];
        segment.words = segment.words
            .slice(0, wordIndex)
            .concat(segment.words.slice(wordIndex + 1));
        segment.dirty = true;
    }

    // Turn a plain word into a named-entity mention: create a fresh mention
    // with a (guessed) label and point the word at it. The type can be
    // corrected afterwards via setMentionLabel.
    function createMention(
        segmentIndex: number,
        wordIndex: number,
        label: string,
    ) {
        const segment = segments.value[segmentIndex];
        const word = segment?.words[wordIndex];
        if (!word) return;
        const id = newId("men");
        mentions.value[id] = { label, score: 1, entityId: null };
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
    }

    // Change the NER label (type) of a mention. The words keep their link;
    // only the shared mention's classification changes.
    function setMentionLabel(
        segmentIndex: number,
        mentionId: string,
        label: string,
    ) {
        const target = mentions.value[mentionId];
        if (!target) return;
        target.label = label;
        const segment = segments.value[segmentIndex];
        if (segment) segment.dirty = true;
    }

    // Mark a word as not to be published: create a fresh redaction with no
    // reason and no explicit time range, and point the word at it. Returns the
    // new redaction id, or an empty string when there is no such word.
    function createRedaction(segmentIndex: number, wordIndex: number): string {
        const segment = segments.value[segmentIndex];
        const word = segment?.words[wordIndex];
        if (!word) return "";
        const id = newId("red");
        redactions.value[id] = { reason: null, start: null, end: null };
        word.redactionId = id;
        segment.dirty = true;
        return id;
    }

    // Grow a redaction onto the word just past its run, left or right. Does
    // nothing at a segment edge, which is what keeps a redaction inside one
    // segment, and nothing when the neighbour already belongs to another
    // redaction. A mention on the neighbour is not consulted: the two
    // occurrence tiers are independent.
    function extendRedaction(
        segmentIndex: number,
        redactionId: string,
        side: "left" | "right",
    ) {
        const segment = segments.value[segmentIndex];
        if (!segment) return;
        const indices = segment.words
            .map((word, i) => (word.redactionId === redactionId ? i : -1))
            .filter((i) => i >= 0);
        if (indices.length === 0) return;
        const target =
            side === "left" ? indices[0] - 1 : indices[indices.length - 1] + 1;
        const neighbour = segment.words[target];
        if (!neighbour || neighbour.redactionId) return;
        neighbour.redactionId = redactionId;
        segment.dirty = true;
    }

    // Shorten a redaction by unlinking the word at one end of its run. Does
    // nothing for a single-word redaction, because a redaction that no word
    // references is invalid; removeRedaction covers that case.
    function reduceRedaction(
        segmentIndex: number,
        redactionId: string,
        side: "left" | "right",
    ) {
        const segment = segments.value[segmentIndex];
        if (!segment) return;
        const indices = segment.words
            .map((word, i) => (word.redactionId === redactionId ? i : -1))
            .filter((i) => i >= 0);
        if (indices.length <= 1) return;
        const target =
            side === "left" ? indices[0] : indices[indices.length - 1];
        segment.words[target].redactionId = null;
        segment.dirty = true;
    }

    // Remove a whole redaction: unlink every word in the segment that carries
    // the redactionId and drop the redaction itself, discarding its reason.
    // The words and their mentions stay.
    function removeRedaction(segmentIndex: number, redactionId: string) {
        const segment = segments.value[segmentIndex];
        if (!segment) return;
        for (const word of segment.words) {
            if (word.redactionId === redactionId) {
                word.redactionId = null;
            }
        }
        delete redactions.value[redactionId];
        segment.dirty = true;
    }

    // Record why a passage is redacted. The reason belongs to the
    // transcript-level entry rather than to one segment, so the segments
    // holding the redaction's words are looked up here and marked dirty, which
    // is what makes a change of reason alone saveable.
    function setRedactionReason(redactionId: string, reason: string) {
        const target = redactions.value[redactionId];
        if (!target) return;
        target.reason = reason;
        segments.value.forEach((segment) => {
            const references = segment.words.some(
                (word) => word.redactionId === redactionId,
            );
            if (references) {
                segment.dirty = true;
            }
        });
    }

    function updateTimecode(
        segmentId: string,
        wordId: string,
        start: number,
        end: number,
    ) {
        const segment = segments.value.find(
            (segment) => segment.id === segmentId,
        );
        if (!segment) return;
        const word = segment.words.find((word) => word.id === wordId);
        if (!word) return;
        word.start = start;
        word.end = end;
        word.dirty = true;
    }

    function addSpeaker(name: string) {
        const trimmed = name.trim();
        if (!trimmed) return;
        if (speakers.value.some((s) => s.name === trimmed)) {
            throw new Error(`Speaker already exists: ${trimmed}`);
        }
        speakers.value.push({
            id: newId("spk"),
            name: trimmed,
            color: SPEAKER_COLORS[
                speakers.value.length % SPEAKER_COLORS.length
            ],
        });
    }

    function renameSpeaker(speakerId: string, newName: string) {
        const trimmed = newName.trim();
        if (!trimmed) return;
        const speaker = speakers.value.find((s) => s.id === speakerId);
        if (!speaker) {
            throw new Error(`Speaker does not exist: ${speakerId}`);
        }
        if (trimmed === speaker.name) return;
        if (
            speakers.value.some((s) => s.id !== speakerId && s.name === trimmed)
        ) {
            throw new Error(`Speaker already exists: ${trimmed}`);
        }

        speaker.name = trimmed;

        // Segments reference the speaker by id, so the rename leaves their
        // speakerId untouched; mark the ones that point at this speaker dirty
        // so the changed name gets persisted on the next save.
        segments.value.forEach((segment) => {
            const references =
                segment.speakerId === speakerId ||
                segment.words.some((word) => word.speakerId === speakerId);
            if (references) {
                segment.dirty = true;
            }
        });
    }

    function deleteSpeaker(speakerId: string) {
        const speaker = speakers.value.find((s) => s.id === speakerId);
        if (!speaker) {
            throw new Error(`Speaker does not exist: ${speakerId}`);
        }

        speakers.value = speakers.value.filter((s) => s.id !== speakerId);

        // Segments and words reference the speaker by id; clear those
        // references and mark the affected segments dirty so the change gets
        // persisted on the next save.
        segments.value.forEach((segment) => {
            let references = false;
            if (segment.speakerId === speakerId) {
                segment.speakerId = null;
                references = true;
            }
            segment.words.forEach((word) => {
                if (word.speakerId === speakerId) {
                    word.speakerId = null;
                    references = true;
                }
            });
            if (references) {
                segment.dirty = true;
            }
        });
    }

    function deleteSegment(segmentId: string) {
        const index = segments.value.findIndex(
            (segment) => segment.id === segmentId,
        );
        const firstPart = segments.value.slice(0, index);
        const lastPart = segments.value.slice(index + 1);
        segments.value = firstPart.concat(lastPart);
    }

    function buildSegment(
        text: string,
        start: number,
        end: number,
    ): TranscriptSegment {
        const speakerId = speakers.value[0]?.id ?? null;
        return {
            id: newId("seg"),
            start: start,
            end: end,
            speakerId: speakerId,
            words: [
                {
                    id: newId("wrd"),
                    start: start,
                    end: start + 3.0,
                    word: text,
                    score: 1.0,
                    speakerId: speakerId,
                },
            ],
        };
    }

    function insertSegmentBefore(
        text: string,
        segmentId: string | null = null,
    ) {
        // Omit segmentId to insert the segment at the end.
        const index =
            typeof segmentId === "string"
                ? segments.value.findIndex(
                      (segment) => segment.id === segmentId,
                  )
                : segments.value.length;

        // start
        const start = index === 0 ? 0.0 : segments.value[index - 1].end;
        // end
        const end =
            index === segments.value.length - 1
                ? start + 15.0
                : segments.value[index].start;

        const newSegment = buildSegment(text, start, end);
        const firstPart = segments.value.slice(0, index);
        const lastPart = segments.value.slice(index);
        segments.value = firstPart.concat(newSegment, lastPart);
    }

    function insertSegmentAfter(text: string, segmentId: string) {
        const index = segments.value.findIndex(
            (segment) => segment.id === segmentId,
        );
        if (index === -1) return;

        // The new segment fills the gap from this segment's end up to the
        // start of its successor, or runs 15s when there is none.
        const start = segments.value[index].end;
        const end =
            index === segments.value.length - 1
                ? start + 15.0
                : segments.value[index + 1].start;

        const newSegment = buildSegment(text, start, end);
        const firstPart = segments.value.slice(0, index + 1);
        const lastPart = segments.value.slice(index + 1);
        segments.value = firstPart.concat(newSegment, lastPart);
    }

    return {
        segments,
        speakers,
        mentions,
        entities,
        redactions,
        mention,
        mentionLabel,
        mentionText,
        redaction,
        redactionText,
        dirtySegmentCount,
        transcriptIsDirty,
        updateWord,
        insertLeft,
        insertRight,
        deleteWord,
        createMention,
        extendMention,
        reduceMention,
        removeMention,
        setMentionLabel,
        createRedaction,
        extendRedaction,
        reduceRedaction,
        removeRedaction,
        setRedactionReason,
        updateTimecode,
        addSpeaker,
        renameSpeaker,
        deleteSpeaker,
        deleteSegment,
        insertSegmentBefore,
        insertSegmentAfter,
    };
});
