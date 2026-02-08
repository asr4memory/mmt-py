export default function cleanTranscript(segments) {
    if (!Array.isArray(segments)) {
        throw TypeError('segments must be an array');
    }

    const result = segments.map((segment) => {
        const cleanedWordsArray = segment.words.map((word) => {
            const clonedWord = {...word};
            delete clonedWord.dirty;
            return clonedWord;
        });

        const clonedSegment = {
            ...segment,
            words: cleanedWordsArray,
        };
        delete clonedSegment.dirty;

        return clonedSegment;
    });

    return result;
}
