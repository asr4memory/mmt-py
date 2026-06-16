import type { RawTranscriptSegment, TranscriptSegment } from "./types";

export default function removeIDsFromTranscript(segments: TranscriptSegment[]): RawTranscriptSegment[] {
    return segments.map((segment) => {
        const { id: _sid, ...segmentWithoutId } = segment;
        return {
            ...segmentWithoutId,
            words: segment.words.map((word) => {
                const { id: _wid, ...wordWithoutId } = word;
                return wordWithoutId;
            }),
        };
    });
}
