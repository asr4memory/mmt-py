import { expect, test } from "vitest";
import removeIDsFromTranscript from "./remove_ids_from_transcript";
import type { TranscriptSegment } from "./types";

test("removeIDsFromTranscript removes ids from segment and word arrays", () => {
    const segments: TranscriptSegment[] = [
        {
            id: "0",
            start: 0.0,
            end: 1.0,
            text: "Hello World!",
            speaker: null,
            words: [
                { id: "0", word: "Hello", start: 0.0, end: 0.5, score: 1 },
                { id: "1", word: "World!", start: 0.5, end: 1.0, score: 1 },
            ],
        },
        {
            id: "1",
            start: 1.5,
            end: 2.5,
            text: "What's up?",
            speaker: null,
            words: [
                { id: "0", word: "What's", start: 1.5, end: 2.0, score: 1 },
                { id: "1", word: "up?", start: 2.0, end: 2.5, score: 1 },
            ],
        },
    ];
    const actual = removeIDsFromTranscript(segments);
    expect(actual[0]).not.toHaveProperty("id");
    expect(actual[0].words[0]).not.toHaveProperty("id");
    expect(actual[0].words[0].word).toBe("Hello");
    expect(actual[1]).not.toHaveProperty("id");
});
