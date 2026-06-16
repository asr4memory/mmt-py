import type { TranscriptSegment } from "./types";

export default function cleanTranscript(segments: TranscriptSegment[]): TranscriptSegment[] {
    return segments.map((segment) => {
        let text = segment.text;

        if (segmentIsDirty(segment)) {
            text = segment.words.map((word) => word.word).join(" ");
        }

        const cleanedWords = segment.words.map((word) => {
            const clonedWord = { ...word };
            delete clonedWord.dirty;
            return clonedWord;
        });

        const clonedSegment = { ...segment, text, words: cleanedWords };
        delete clonedSegment.dirty;

        return clonedSegment;
    });
}

function segmentIsDirty(segment: TranscriptSegment): boolean {
    return segment.dirty === true || segment.words.some((word) => word.dirty === true);
}
