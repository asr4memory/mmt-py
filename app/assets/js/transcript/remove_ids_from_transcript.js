export default function removeIDsFromTranscript(segments) {
    if (!Array.isArray(segments)) {
        throw TypeError("segments must be an array");
    }

    const result = segments.map((segment, index) => {
        const words = segment.words.map((word) => {
            const newWord = { ...word };
            delete newWord.id;
            return newWord;
        });

        const newSegment = {
            ...segment,
            words: words,
        };
        delete newSegment.id;
        return newSegment;
    });

    return result;
}
