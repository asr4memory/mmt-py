import type { TranscriptSegment } from "./types";

export default function findPlaybackPosition(
    segments: TranscriptSegment[],
    time: number,
): { segmentIdx: number; wordIdx: number } {
    let low = 0;
    let high = segments.length - 1;
    let segmentIdx = -1;

    while (low <= high) {
        const mid = (low + high) >> 1;
        if (segments[mid].start <= time) {
            segmentIdx = mid;
            low = mid + 1;
        } else {
            high = mid - 1;
        }
    }

    if (segmentIdx === -1 || time > segments[segmentIdx].end) {
        return { segmentIdx: -1, wordIdx: -1 };
    }

    const wordIdx = segments[segmentIdx].words.findIndex(
        (word) => word.start <= time && time <= word.end,
    );

    return { segmentIdx, wordIdx };
}
