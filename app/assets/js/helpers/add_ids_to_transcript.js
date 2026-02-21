/**
 * Adds sequential string IDs to an array of transcript segments and their words.
 *
 * @param {Object[]} segments - The transcript segments to enrich.
 * @param {Object[]} segments[].words - The words within each segment.
 * @returns {Object[]} A new array of segments, each with an added `id` property (zero-indexed string),
 *   and each word within `words` also given a zero-indexed string `id`.
 * @throws {TypeError} If `segments` is not an array.
 *
 * @example
 * const segments = [{ text: "Hello world", words: [{ text: "Hello" }, { text: "world" }] }];
 * addIDsToTranscript(segments);
 * // => [{ text: "Hello world", id: "0", words: [{ text: "Hello", id: "0" }, { text: "world", id: "1" }] }]
 */
export default function addIDsToTranscript(segments) {
    if (!Array.isArray(segments)) {
        throw TypeError("segments must be an array");
    }

    const enrichedSegments = segments.map((segment, index) => ({
        ...segment,
        id: index.toString(),
        words: segment.words.map((word, index) => ({
            ...word,
            id: index.toString(),
        })),
    }));

    return enrichedSegments;
}
