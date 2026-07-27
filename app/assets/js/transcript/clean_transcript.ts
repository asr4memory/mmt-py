import type { TranscriptSegment } from "./types";

export default function cleanTranscript(segments: TranscriptSegment[]): TranscriptSegment[] {
    return segments.map((segment) => {
        const cleanedWords = segment.words.map((word) => {
            const clonedWord = { ...word };
            delete clonedWord.dirty;
            return clonedWord;
        });

        const clonedSegment = { ...segment, words: cleanedWords };
        delete clonedSegment.dirty;

        return clonedSegment;
    });
}
