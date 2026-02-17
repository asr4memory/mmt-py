import { defineStore } from "pinia";

export const useTranscriptStore = defineStore("transcript", {
    state: () => ({
        segments: [],
    }),
    getters: {
        transcriptIsDirty() {
            return this.segments.some((segment) => {
                return (
                    segment.dirty === true ||
                    segment.words.some((word) => word.dirty === true)
                );
            });
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
        deleteWord(segmentIndex, wordIndex) {
            const segment = this.segments[segmentIndex];
            segment.words = segment.words
                .slice(0, wordIndex)
                .concat(segment.words.slice(wordIndex + 1));
            segment.dirty = true;
        },
    },
});
