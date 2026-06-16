import type { RawTranscriptSegment, TranscriptSegment } from "./types";

export default function addIDsToTranscript(segments: RawTranscriptSegment[]): TranscriptSegment[] {
    return segments.map((segment, index) => ({
        ...segment,
        id: index.toString(),
        words: segment.words.map((word, wordIndex) => ({
            ...word,
            id: wordIndex.toString(),
        })),
    }));
}
