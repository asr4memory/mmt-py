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
            const word = segment.words[wordIndex];
            const oldWord = word.word;

            if (trimmedText === '') {
                segment.words = segment.words.slice(0, wordIndex).concat(segment.words.slice(wordIndex + 1));
            } else {
                word.word = trimmedText;
            }

            if (trimmedText !== oldWord) {
                word.dirty = true;
            }
        },
    },
});
