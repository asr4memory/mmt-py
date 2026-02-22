import { defineStore } from "pinia";

export const useTranscriptStore = defineStore("transcript", {
    state: () => ({
        segments: [],
    }),
    getters: {
        dirtySegmentCount() {
            const dirtySegments = this.segments.filter(
                (segment) =>
                    segment.dirty === true ||
                    segment.words.some((word) => word.dirty === true),
            );
            return dirtySegments.length;
        },
        transcriptIsDirty() {
            return this.dirtySegmentCount > 0;
        },
    },
    actions: {
        updateWord(segmentIndex, wordIndex, text) {
            const trimmedText = text.trim();
            const segment = this.segments[segmentIndex];
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
        },
        insertLeft(segmentIndex, wordIndex) {
            const segment = this.segments[segmentIndex];
            const relativeWord = segment.words[wordIndex];
            const newWord = {
                // id is still missing!
                start: relativeWord.start - 0.5,
                end: relativeWord.start - 0.05,
                word: 'newword',
                score: 1,
                dirty: true,
            }
            segment.words = segment.words
                .slice(0, wordIndex)
                .concat(newWord)
                .concat(segment.words.slice(wordIndex));
        },
        insertRight(segmentIndex, wordIndex) {
            const segment = this.segments[segmentIndex];
            const relativeWord = segment.words[wordIndex];
            const newWord = {
                // id is still missing!
                start: relativeWord.end + 0.05,
                end: relativeWord.end + 0.5,
                word: 'newword',
                score: 1,
                dirty: true,
            }
            segment.words = segment.words
                .slice(0, wordIndex + 1)
                .concat(newWord)
                .concat(segment.words.slice(wordIndex + 1));
        },
        deleteWord(segmentIndex, wordIndex) {
            const segment = this.segments[segmentIndex];
            segment.words = segment.words
                .slice(0, wordIndex)
                .concat(segment.words.slice(wordIndex + 1));
            segment.dirty = true;
        },
        updateTimecode(segmentId, wordId, start, end) {
            const segment = this.segments.find((segment) => segment.id === segmentId);
            const word = segment.words.find((word) => word.id === wordId);
            word.start = start;
            word.end = end;
            word.dirty = true;
        }
    },
});
