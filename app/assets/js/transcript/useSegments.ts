import { computed, type Ref } from "vue";

import { newId } from "./new_id";
import type { Speaker, TranscriptSegment } from "./types";

// The segment list itself: which segments are unsaved, inserting and deleting
// segments.
export function useSegments(
    segments: Ref<TranscriptSegment[]>,
    speakers: Ref<Speaker[]>,
    pruneOrphans: () => void,
) {
    const dirtySegmentCount = computed(() => {
        const dirtySegments = segments.value.filter(
            (segment) =>
                segment.dirty === true ||
                segment.words.some((word) => word.dirty === true),
        );
        return dirtySegments.length;
    });

    // Removes the dirty flags in place, so only the segments that were
    // changed re-render after a save.
    function markSegmentsSaved() {
        for (const segment of segments.value) {
            delete segment.dirty;
            for (const word of segment.words) {
                delete word.dirty;
            }
        }
    }

    function deleteSegment(segmentId: string) {
        const index = segments.value.findIndex(
            (segment) => segment.id === segmentId,
        );
        const firstPart = segments.value.slice(0, index);
        const lastPart = segments.value.slice(index + 1);
        segments.value = firstPart.concat(lastPart);
        pruneOrphans();
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

    // Merges the segment into the one before it. The predecessor keeps its id
    // and its speaker, the word lists are concatenated in order and the time
    // range is extended to the end of the merged segment. Every word carries
    // its own speakerId, so the merge does not change who said a word, even
    // when the two segments have different speakers.
    //
    // Does nothing when the segment does not exist or is the first one, since
    // there is then nothing to merge it into.
    function mergeSegmentIntoPrevious(segmentId: string) {
        const index = segments.value.findIndex(
            (segment) => segment.id === segmentId,
        );
        if (index <= 0) return;

        const previous = segments.value[index - 1];
        const current = segments.value[index];

        // Segments are in ascending time order and do not overlap, so the
        // merged range runs from the start of the predecessor to the end of
        // the merged segment.
        const merged: TranscriptSegment = {
            ...previous,
            start: previous.start,
            end: current.end,
            words: previous.words.concat(current.words),
            dirty: true,
        };

        const firstPart = segments.value.slice(0, index - 1);
        const lastPart = segments.value.slice(index + 1);
        segments.value = firstPart.concat(merged, lastPart);
    }

    // Splits the segment after the word at the given position: the original
    // segment keeps its id and the words up to and including that word, and a
    // new segment takes the rest. The new segment copies the speaker of the
    // original; every word keeps its own speakerId. The time ranges follow the
    // words, so the first part ends where the split word ends and the second
    // part begins where the word after it begins.
    //
    // Does nothing when the segment does not exist, when the position is not a
    // word of it, when it is the last word, since the second part would then
    // hold no words, or when the split would fall inside a mention or a
    // redaction. A redaction whose words lie in two segments is rejected by
    // the stored format, and the text of a mention is read from one segment,
    // so both runs have to stay whole.
    function splitSegmentAfterWord(segmentId: string, wordIndex: number) {
        const index = segments.value.findIndex(
            (segment) => segment.id === segmentId,
        );
        if (index === -1) return;

        const segment = segments.value[index];
        const word = segment.words[wordIndex];
        const nextWord = segment.words[wordIndex + 1];
        if (!word || !nextWord) return;
        if (word.mentionId && word.mentionId === nextWord.mentionId) return;
        if (word.redactionId && word.redactionId === nextWord.redactionId) {
            return;
        }

        const firstSegment: TranscriptSegment = {
            ...segment,
            end: word.end,
            words: segment.words.slice(0, wordIndex + 1),
            dirty: true,
        };
        const secondSegment: TranscriptSegment = {
            ...segment,
            id: newId("seg"),
            start: nextWord.start,
            end: segment.end,
            words: segment.words.slice(wordIndex + 1),
            dirty: true,
        };

        const firstPart = segments.value.slice(0, index);
        const lastPart = segments.value.slice(index + 1);
        segments.value = firstPart.concat(
            firstSegment,
            secondSegment,
            lastPart,
        );
    }

    return {
        dirtySegmentCount,
        markSegmentsSaved,
        deleteSegment,
        insertSegmentBefore,
        insertSegmentAfter,
        mergeSegmentIntoPrevious,
        splitSegmentAfterWord,
    };
}
