export default function cleanTranscript(segments) {
    if (!Array.isArray(segments)) {
        throw TypeError("segments must be an array");
    }

    const result = segments.map((segment) => {
        let text = segment.text;

        if (segmentIsDirty(segment)) {
            const wordArray = segment.words.map((word) => word.word);
            text = wordArray.join(" ");
        }

        const cleanedWordsArray = segment.words.map((word) => {
            const clonedWord = { ...word };
            delete clonedWord.dirty;
            return clonedWord;
        });

        const clonedSegment = {
            ...segment,
            text,
            words: cleanedWordsArray,
        };
        delete clonedSegment.dirty;

        return clonedSegment;
    });

    return result;
}

function segmentIsDirty(segment) {
    return (
        segment.dirty === true ||
        segment.words.some((word) => word.dirty === true)
    );
}
