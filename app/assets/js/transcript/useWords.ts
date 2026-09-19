import type { Ref } from "vue";

import { newId } from "./new_id";
import type { TranscriptSegment, TranscriptWord } from "./types";

// Editing operations on the words of a segment: the text of a word, the
// insertion and deletion of words and the time range of a single word.
export function useWords(
    segments: Ref<TranscriptSegment[]>,
    pruneOrphans: () => void,
) {
    // The text of one word has changed; the word keeps its id and its times.
    function renameWord(segmentIndex: number, wordIndex: number, text: string) {
        const segment = segments.value[segmentIndex];
        const word = { ...segment.words[wordIndex], word: text, dirty: true };
        segment.words = segment.words
            .slice(0, wordIndex)
            .concat(word)
            .concat(segment.words.slice(wordIndex + 1));
        segment.dirty = true;
    }

    // The text of one word now contains several words; replace it by one word
    // per part. Each part needs its own id so ids stay unique in the content.
    function splitWord(
        segmentIndex: number,
        wordIndex: number,
        parts: string[],
    ) {
        const segment = segments.value[segmentIndex];
        const oldWord = segment.words[wordIndex];
        const newWords = parts.map((part) => ({
            ...oldWord,
            id: newId("wrd"),
            word: part,
            dirty: true,
        }));
        segment.words = segment.words
            .slice(0, wordIndex)
            .concat(newWords)
            .concat(segment.words.slice(wordIndex + 1));
        segment.dirty = true;
    }

    function applyWordEdit(
        segmentIndex: number,
        wordIndex: number,
        text: string,
    ) {
        const trimmedText = text.trim();

        if (trimmedText === "") {
            deleteWord(segmentIndex, wordIndex);
            return;
        }

        const words = trimmedText.split(/\s+/);

        if (words.length === 1) {
            renameWord(segmentIndex, wordIndex, words[0]);
        } else {
            splitWord(segmentIndex, wordIndex, words);
        }
    }

    function deleteWord(segmentIndex: number, wordIndex: number) {
        const segment = segments.value[segmentIndex];
        segment.words = segment.words
            .slice(0, wordIndex)
            .concat(segment.words.slice(wordIndex + 1));
        segment.dirty = true;
        pruneOrphans();
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

    return {
        applyWordEdit,
        deleteWord,
        insertLeft,
        insertRight,
        updateTimecode,
    };
}
