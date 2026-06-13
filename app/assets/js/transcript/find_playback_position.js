/**
 * Locates the segment and word containing a playback time.
 *
 * Binary-searches the segments (sorted by start time), then scans the
 * words of the matching segment, so it stays cheap for large
 * transcripts even when called on every time update.
 *
 * @param {Object[]} segments - The transcript segments.
 * @param {number} time - The playback position in seconds.
 * @returns {{segmentIdx: number, wordIdx: number}} Indices of the
 *     segment and word containing `time`, each -1 if there is none
 *     (`wordIdx` can be -1 with a valid `segmentIdx` when the time
 *     falls into a gap between words).
 */
export default function findPlaybackPosition(segments, time) {
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
