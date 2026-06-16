import { defineStore } from "pinia";
import { computed, ref } from "vue";

import getAllSpeakers from "./get_all_speakers";
import type { TranscriptSegment, TranscriptWord } from "./types";

const SPEAKER_COLORS = ["#5b9bd5", "#70ad47", "#ed7d31", "#9b59b6", "#17a589"];

export interface Speaker {
    name: string;
    color: string;
}

export const useTranscriptStore = defineStore("transcript", () => {
    const segments = ref<TranscriptSegment[]>([]);
    const speakers = ref<Speaker[]>([]);

    const dirtySegmentCount = computed(() => {
        const dirtySegments = segments.value.filter(
            (segment) =>
                segment.dirty === true ||
                segment.words.some((word) => word.dirty === true),
        );
        return dirtySegments.length;
    });

    const transcriptIsDirty = computed(() => dirtySegmentCount.value > 0);

    function updateWord(
        segmentIndex: number,
        wordIndex: number,
        text: string,
    ) {
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
            // Former word contains more than one word now; split them up.
            const splitWords = trimmedText.split(" ");
            const wordObjects = splitWords.map((w) => ({
                ...word,
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
        const newWord = {
            // id is still missing!
            start: relativeWord.start - 0.5,
            end: relativeWord.start - 0.05,
            word: "newword",
            score: 1,
            dirty: true,
        } as TranscriptWord;
        segment.words = segment.words
            .slice(0, wordIndex)
            .concat(newWord)
            .concat(segment.words.slice(wordIndex));
    }

    function insertRight(segmentIndex: number, wordIndex: number) {
        const segment = segments.value[segmentIndex];
        const relativeWord = segment.words[wordIndex];
        const newWord = {
            // id is still missing!
            start: relativeWord.end + 0.05,
            end: relativeWord.end + 0.5,
            word: "newword",
            score: 1,
            dirty: true,
        } as TranscriptWord;
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

    function updateTimecode(
        segmentId: string | number,
        wordId: string | number,
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
            name: trimmed,
            color: SPEAKER_COLORS[
                speakers.value.length % SPEAKER_COLORS.length
            ],
        });
    }

    function renameSpeaker(oldName: string, newName: string) {
        const trimmed = newName.trim();
        if (!trimmed) return;
        if (trimmed === oldName) return;
        const speaker = speakers.value.find((s) => s.name === oldName);
        if (!speaker) {
            throw new Error(`Speaker does not exist: ${oldName}`);
        }
        if (speakers.value.some((s) => s.name === trimmed)) {
            throw new Error(`Speaker already exists: ${trimmed}`);
        }

        speaker.name = trimmed;

        segments.value.forEach((segment) => {
            let changed = false;
            if (segment.speaker === oldName) {
                segment.speaker = trimmed;
                changed = true;
            }
            segment.words.forEach((word) => {
                if (word.speaker === oldName) {
                    word.speaker = trimmed;
                    changed = true;
                }
            });
            if (changed) {
                segment.dirty = true;
            }
        });
    }

    function extractSpeakers() {
        speakers.value = getAllSpeakers(segments.value).map((name, i) => ({
            name,
            color: SPEAKER_COLORS[i % SPEAKER_COLORS.length],
        }));
    }

    function deleteSegment(segmentId: string | number) {
        const index = segments.value.findIndex(
            (segment) => segment.id === segmentId,
        );
        const firstPart = segments.value.slice(0, index);
        const lastPart = segments.value.slice(index + 1);
        segments.value = firstPart.concat(lastPart);
    }

    function insertSegmentBefore(
        text: string,
        segmentId: string | number | null = null,
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

        const speaker = speakers.value[0]?.name || null;
        const newSegment: TranscriptSegment = {
            id: "newSeg",
            start: start,
            end: end,
            text: text,
            speaker: speaker,
            words: [
                {
                    id: "newWord",
                    start: start,
                    end: start + 3.0,
                    word: text,
                    score: 1.0,
                    speaker: speaker,
                },
            ],
        };
        const firstPart = segments.value.slice(0, index);
        const lastPart = segments.value.slice(index);
        segments.value = firstPart.concat(newSegment, lastPart);
    }

    return {
        segments,
        speakers,
        dirtySegmentCount,
        transcriptIsDirty,
        updateWord,
        insertLeft,
        insertRight,
        deleteWord,
        updateTimecode,
        addSpeaker,
        renameSpeaker,
        extractSpeakers,
        deleteSegment,
        insertSegmentBefore,
    };
});
