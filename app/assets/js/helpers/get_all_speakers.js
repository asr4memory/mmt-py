/**
 * Extracts speaker strings from a transcript.
 *
 * @param {Object[]} segments - The transcript segments.
 * @returns {string[]} An array of speaker strings.
 * @throws {TypeError} If `segments` is not an array.
 */
export default function getAllSpeakers(segments) {
    if (!Array.isArray(segments)) {
        throw TypeError("segments must be an array");
    }

    const speakers = new Array();

    segments.forEach((segment) => {
        if (
            isValidSpeaker(segment.speaker) &&
            !speakers.includes(segment.speaker)
        ) {
            speakers.push(segment.speaker);
        }

        segment.words.forEach((word) => {
            if (
                isValidSpeaker(word.speaker) &&
                !speakers.includes(word.speaker)
            ) {
                speakers.push(word.speaker);
            }
        });
    });

    console.log(speakers);

    return speakers.toSorted();
}

function isValidSpeaker(speaker) {
    return typeof speaker === "string" && speaker.trim() !== "";
}
