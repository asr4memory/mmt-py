import { expect, test } from "vitest";
import addIDsToTranscript from "./add_ids_to_transcript";

test("addIDsToTranscript adds ids to segment and word arrays", () => {
    const segments = [
        {
            text: "Hello World!",
            words: [{ word: "Hello" }, { word: "World!" }],
        },
        { text: "What's up?", words: [{ word: "What's" }, { word: "up?" }] },
    ];
    const actual = addIDsToTranscript(segments);
    const expected = [
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
    expect(actual).toEqual(expected);
});
