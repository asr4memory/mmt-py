import { expect, test } from "vitest";
import removeIDsFromTranscript from "./remove_ids_from_transcript";

test("removeIDsFromTranscript removes ids from segment and word arrays", () => {
    const segments = [
        {
            id: "0",
            text: "Hello World!",
            words: [
                { id: "0", word: "Hello" },
                { id: "1", word: "World!" },
            ],
        },
        {
            id: "1",
            text: "What's up?",
            words: [
                { id: "0", word: "What's" },
                { id: "1", word: "up?" },
            ],
        },
    ];
    const actual = removeIDsFromTranscript(segments);
    const expected = [
        {
            text: "Hello World!",
            words: [{ word: "Hello" }, { word: "World!" }],
        },
        { text: "What's up?", words: [{ word: "What's" }, { word: "up?" }] },
    ];
    expect(actual).toEqual(expected);
});
