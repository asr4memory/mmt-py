import { ref, type Ref } from "vue";

import { newId } from "./new_id";
import type { TranscriptSegment, TranscriptWord } from "./types";

// Placeholder text of an inserted word. The schema rejects an empty word,
// and the input opens with this text selected, so typing replaces it.
const NEW_WORD_TEXT = "…";

// Editing operations on the words of a segment: the text of a word, the
// insertion and deletion of words and the time range of a single word.
export function useWords(
    segments: Ref<TranscriptSegment[]>,
    pruneOrphans: () => void,
) {
    // The id of the word whose input is to be opened for editing. An insertion
    // sets it, and the word component clears it once it has focused the input.
    const focusWordId = ref<string | null>(null);

    function clearFocusWord() {
        focusWordId.value = null;
    }

    // The text of one word has changed; the word keeps its id and its times.
    function renameWord(segmentIndex: number, wordIndex: number, text: string) {
        const segment = segments.value[segmentIndex];
        const word = {
            ...segment.words[wordIndex],
            word: text,
            // The text was typed by hand, so the recognizer's confidence in
            // the word it produced no longer applies.
            score: 1,
            dirty: true,
        };
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
        // The parts share the time range of the word they came from, divided
        // in proportion to their character lengths. The last part ends where
        // the original word ended, so rounding cannot move the boundary of the
        // range.
        const duration = oldWord.end - oldWord.start;
        const totalCharacters = parts.reduce(
            (sum, part) => sum + part.length,
            0,
        );
        const newWords: TranscriptWord[] = [];
        let start = oldWord.start;
        for (const [index, part] of parts.entries()) {
            const isLastPart = index === parts.length - 1;
            const end = isLastPart
                ? oldWord.end
                : start + (duration * part.length) / totalCharacters;
            newWords.push({
                ...oldWord,
                id: newId("wrd"),
                // mentionId and redactionId are inherited deliberately: a
                // split word keeps its annotations on every part.
                word: part,
                // None of the parts is the word the recognizer produced.
                score: 1,
                start: start,
                end: end,
                dirty: true,
            });
            start = end;
        }
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

    // A word inserted between two words that belong to the same mention, or to
    // the same redaction, joins it, so the run stays contiguous. At either end
    // of a run, or between two different runs, the new word stays unlinked.
    function sharedAnnotations(
        segment: TranscriptSegment,
        leftIndex: number,
        rightIndex: number,
    ) {
        const left = segment.words[leftIndex];
        const right = segment.words[rightIndex];
        const sharesMention =
            !!left?.mentionId && left.mentionId === right?.mentionId;
        const sharesRedaction =
            !!left?.redactionId && left.redactionId === right?.redactionId;
        return {
            mentionId: sharesMention ? left.mentionId : null,
            redactionId: sharesRedaction ? left.redactionId : null,
        };
    }

    // Put a word into the list of a segment at the given position.
    function insertWordAt(
        segmentIndex: number,
        position: number,
        newWord: TranscriptWord,
    ) {
        const segment = segments.value[segmentIndex];
        segment.words = segment.words
            .slice(0, position)
            .concat(newWord)
            .concat(segment.words.slice(position));
    }

    // Insert a fresh word before the given one. It takes the first third of
    // its neighbour's interval, so it stays inside the segment and clear of
    // every other word, and the neighbour keeps two thirds of its duration.
    function insertLeft(segmentIndex: number, wordIndex: number) {
        const segment = segments.value[segmentIndex];
        const neighbour = segment.words[wordIndex];
        const share = (neighbour.end - neighbour.start) / 3;
        const annotations = sharedAnnotations(
            segment,
            wordIndex - 1,
            wordIndex,
        );
        const newWord: TranscriptWord = {
            id: newId("wrd"),
            start: neighbour.start,
            end: neighbour.start + share,
            word: NEW_WORD_TEXT,
            score: 1,
            speakerId: neighbour.speakerId,
            mentionId: annotations.mentionId,
            redactionId: annotations.redactionId,
            dirty: true,
        };
        neighbour.start = neighbour.start + share;
        neighbour.dirty = true;
        insertWordAt(segmentIndex, wordIndex, newWord);
        focusWordId.value = newWord.id;
    }

    // Insert a fresh word after the given one. It takes the last third of its
    // neighbour's interval, on the same grounds as insertLeft.
    function insertRight(segmentIndex: number, wordIndex: number) {
        const segment = segments.value[segmentIndex];
        const neighbour = segment.words[wordIndex];
        const share = (neighbour.end - neighbour.start) / 3;
        const annotations = sharedAnnotations(
            segment,
            wordIndex,
            wordIndex + 1,
        );
        const newWord: TranscriptWord = {
            id: newId("wrd"),
            start: neighbour.end - share,
            end: neighbour.end,
            word: NEW_WORD_TEXT,
            score: 1,
            speakerId: neighbour.speakerId,
            mentionId: annotations.mentionId,
            redactionId: annotations.redactionId,
            dirty: true,
        };
        neighbour.end = neighbour.end - share;
        neighbour.dirty = true;
        insertWordAt(segmentIndex, wordIndex + 1, newWord);
        focusWordId.value = newWord.id;
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
        focusWordId,
        clearFocusWord,
        applyWordEdit,
        deleteWord,
        insertLeft,
        insertRight,
        updateTimecode,
    };
}
