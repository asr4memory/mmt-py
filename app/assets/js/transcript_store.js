import { defineStore } from "pinia";

export const useTranscriptStore = defineStore("transcript", {
    state: () => ({
        segments: [],
    }),
    getters: {},
    actions: {
        updateWord(segmentIndex, wordIndex, text) {
            const word = this.segments[segmentIndex].words[wordIndex];
            word.word = text;
        },
    },
});
