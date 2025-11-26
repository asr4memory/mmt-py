import { defineStore } from "pinia";

export const useTranscriptStore = defineStore("transcript", {
    state: () => ({
        segments: [],
    }),
    getters: {},
    actions: {
        updateWord(segmentIndex, wordIndex, text) {
            const trimmedText = text.trim();
            const segment = this.segments[segmentIndex];
            const word = {
                ...segment.words[wordIndex]
            };
            const oldWord = word.word;

            if (trimmedText !== oldWord) {
                word.dirty = true;
            }

            if (trimmedText === '') {
                segment.words = segment.words.slice(0, wordIndex).concat(segment.words.slice(wordIndex + 1));
            } else if (trimmedText.split(' ').length === 1) {
                word.word = trimmedText;
                segment.words = segment.words.slice(0, wordIndex)
                    .concat(word)
                    .concat(segment.words.slice(wordIndex + 1));
            } else {
                const splitWords = trimmedText.split(' ');
                const wordObjects = splitWords.map(w => ({
                    ...word,
                    word: w,
                }));
                const combined = segment.words.slice(0, wordIndex)
                    .concat(wordObjects)
                    .concat(segment.words.slice(wordIndex + 1));

                segment.words = combined;
            }
        },
    },
});
