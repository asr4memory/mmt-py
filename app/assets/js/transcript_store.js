import { defineStore } from "pinia";

import getAllSpeakers from "./helpers/get_all_speakers";

const SPEAKER_COLORS = [
    "#5b9bd5",
    "#70ad47",
    "#ed7d31",
    "#9b59b6",
    "#17a589",
];

export const useTranscriptStore = defineStore("transcript", {
    state: () => ({
        segments: [],
        speakers: [],
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
                word: "newword",
                score: 1,
                dirty: true,
            };
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
                word: "newword",
                score: 1,
                dirty: true,
            };
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
            const segment = this.segments.find(
                (segment) => segment.id === segmentId,
            );
            const word = segment.words.find((word) => word.id === wordId);
            word.start = start;
            word.end = end;
            word.dirty = true;
        },
        addSpeaker(name) {
            const trimmed = name.trim();
            if (!trimmed) return;
            if (this.speakers.some((s) => s.name === trimmed)) {
                throw new Error(`Speaker already exists: ${trimmed}`);
            }
            this.speakers.push({
                name: trimmed,
                color: SPEAKER_COLORS[this.speakers.length % SPEAKER_COLORS.length],
            });
        },
        renameSpeaker(oldName, newName) {
            const trimmed = newName.trim();
            if (!trimmed) return;
            if (trimmed === oldName) return;
            const speaker = this.speakers.find((s) => s.name === oldName);
            if (!speaker) {
                throw new Error(`Speaker does not exist: ${oldName}`);
            }
            if (this.speakers.some((s) => s.name === trimmed)) {
                throw new Error(`Speaker already exists: ${trimmed}`);
            }

            speaker.name = trimmed;

            this.segments.forEach((segment) => {
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
        },
        extractSpeakers() {
            this.speakers = getAllSpeakers(this.segments).map((name, i) => ({
                name,
                color: SPEAKER_COLORS[i % SPEAKER_COLORS.length],
            }));
        },
        deleteSegment(segmentId) {
            const index = this.segments.findIndex(
                (segment) => segment.id === segmentId,
            );
            const firstPart = this.segments.slice(0, index);
            const lastPart = this.segments.slice(index + 1);
            const result = firstPart.concat(lastPart);
            this.segments = result;
        },
        insertSegmentBefore(text, segmentId = null) {
            // Omit segmentId to insert the segment at the end.
            const index =
                typeof segmentId === "string"
                    ? this.segments.findIndex(
                          (segment) => segment.id === segmentId,
                      )
                    : this.segments.length;

            // start
            const start = index === 0 ? 0.0 : this.segments[index - 1].end;
            // end
            const end =
                index === this.segments.length - 1
                    ? start + 15.0
                    : this.segments[index].start;

            const speaker = this.speakers[0]?.name || null;
            const newSegment = {
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
            const firstPart = this.segments.slice(0, index);
            const lastPart = this.segments.slice(index);
            const result = firstPart.concat(newSegment, lastPart);
            this.segments = result;
        },
    },
});
